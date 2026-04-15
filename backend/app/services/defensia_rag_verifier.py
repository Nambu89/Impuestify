"""DefensIA RAG Verifier (Wave 2B, T2B-001/002/003).

Verificador anti-alucinacion para DefensIA. Cada regla del motor (R001-R030)
produce un ``ArgumentoCandidato`` con una cita normativa SEMANTICA y libre
(p.ej. "motivacion insuficiente del acto administrativo tributario"). Esta
cita NO es una referencia canonica — la resolucion a "Art. 102.2.c LGT" se
hace aqui, consultando el corpus RAG via ``HybridRetriever``.

Funcionamiento
--------------
1. Para cada candidato, ejecutamos ``HybridRetriever.search`` con
   ``candidato.cita_normativa_propuesta`` como query.
2. Si el mejor chunk devuelve ``similarity >= CONFIANZA_MIN`` (0.7), el
   argumento se acepta y se materializa como ``ArgumentoVerificado`` con
   la cita canonica del chunk top-1 y la similarity como ``confianza``.
3. Si el mejor chunk devuelve ``similarity < CONFIANZA_MIN``, el argumento
   se descarta silenciosamente: NO aparece en el dictamen ni en el escrito
   exportado, pero queda logeado en la tabla ``defensia_rag_log`` para
   auditoria. El usuario nunca ve "argumento no soportado".
4. Los errores del retriever (Upstash caido, timeout, etc.) se tratan como
   descarte con razon ``retriever_error``; nunca tumban el pipeline.
5. Los errores de log (Turso caido) se tragan con warning — el log es
   best-effort y jamas puede romper la verificacion.

Invariantes
-----------
- ``CONFIANZA_MIN = 0.7`` literal (decision producto B1, plan Parte 2).
  El corte es ``>=`` — confianza exactamente 0.7 se acepta; 0.699 se rechaza.
- Los candidatos descartados NO aparecen en la salida de ``verify_all``.
- La salida es siempre ``list[ArgumentoVerificado]`` donde cada elemento
  cumple ``confianza >= CONFIANZA_MIN``.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-001/002/003
Invariante #3 del plan v2 (umbral 0.7, no 0.6).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.defensia import ArgumentoCandidato, ArgumentoVerificado

logger = logging.getLogger(__name__)


CONFIANZA_MIN: float = 0.7
"""Umbral minimo de confianza para aceptar un argumento.

Constante dura del producto (decision B1 del plan Parte 2): si la
similarity del mejor chunk devuelto por ``HybridRetriever`` es
estrictamente menor que ``0.7``, el argumento se descarta silenciosamente.
No se incluye en el dictamen ni en el escrito exportado, pero queda
logeado en ``defensia_rag_log`` para auditoria y ajuste de reglas en
sesiones futuras.

NO cambiar a 0.6 ni a ningun otro valor sin revisar la spec completa —
todo el ecosistema de tests T2B-001/T2B-002/T2B-003 asume 0.7 exacto.
"""


_MAX_CITA_VERIFICADA_CHARS: int = 1000
"""Longitud maxima del snippet de texto que guardamos como cita verificada.

El objetivo es evitar meter paginas enteras en el argumento final —
1000 caracteres suelen sobrar para cubrir 1-2 apartados legales completos.
"""


_MAX_CITA_LOG_CHARS: int = 500
"""Longitud maxima de la cita propuesta que se persiste en el log.

El log es para auditoria, no para reconstruir el escrito — 500 caracteres
bastan para identificar de que cita se trataba. Mas alla inflariamos la
tabla sin ganancia.
"""


class DefensiaRagVerifier:
    """Verificador anti-alucinacion contra el corpus RAG.

    Se construye con un ``HybridRetriever`` (FTS5 + Upstash Vector, con
    RRF fusion) y opcionalmente un cliente Turso para logear auditoria a
    ``defensia_rag_log``. Si ``db_client`` es ``None`` el verificador
    funciona en "modo silencioso" — util para tests ligeros.
    """

    def __init__(self, retriever: Any, db_client: Any = None):
        """
        Args:
            retriever: una instancia de ``HybridRetriever`` (o compatible)
                con un metodo asincrono ``search(query, query_embedding,
                k, territory_filter)`` que devuelve una lista de dicts
                con al menos ``similarity``, ``text``, ``title`` y
                ``source``.
            db_client: cliente Turso con ``execute(sql, params)`` async.
                Si es ``None``, los logs de auditoria se omiten.
        """
        self.retriever = retriever
        self.db = db_client

    # ------------------------------------------------------------------
    # Verificacion de UN candidato
    # ------------------------------------------------------------------

    async def verify_one(
        self,
        candidato: ArgumentoCandidato,
        *,
        expediente_id: Optional[str] = None,
        top_k: int = 5,
        territory_filter: Optional[str] = None,
    ) -> Optional[ArgumentoVerificado]:
        """Verifica UN candidato contra el corpus RAG.

        Args:
            candidato: el argumento producido por una regla determinista.
            expediente_id: id del expediente para trazabilidad en
                ``defensia_rag_log`` (FK opcional). Si es ``None``, el
                log usa el valor vacio — el modelo permite strings.
            top_k: numero de chunks a recuperar del retriever (default 5,
                suficiente para elegir el mejor con margen).
            territory_filter: filtro opcional de territorio (AEAT, CCAA...)
                que se propaga al retriever.

        Returns:
            ``ArgumentoVerificado`` si la confianza del mejor chunk es
            ``>= CONFIANZA_MIN``. ``None`` en caso contrario (descarte
            silencioso).
        """
        query = candidato.cita_normativa_propuesta

        # Paso 1: consultar al retriever. Cualquier excepcion se trata
        # como descarte + log + None — el verificador nunca debe tumbar
        # el pipeline por un fallo externo (Upstash caido, timeout, etc.).
        try:
            results = await self.retriever.search(
                query=query,
                query_embedding=None,
                k=top_k,
                territory_filter=territory_filter,
            )
        except Exception as exc:
            logger.warning(
                "RAG verifier: error en retriever para regla %s: %s",
                candidato.regla_id, exc,
            )
            await self._log(
                candidato,
                expediente_id=expediente_id,
                soportado=False,
                confianza=0.0,
                razonamiento=f"retriever_error: {exc}",
            )
            return None

        if not results:
            await self._log(
                candidato,
                expediente_id=expediente_id,
                soportado=False,
                confianza=0.0,
                razonamiento="sin_resultados",
            )
            return None

        # Paso 2: evaluar similarity del mejor chunk.
        best = results[0]
        try:
            top_similarity = float(best.get("similarity", 0.0) or 0.0)
        except (TypeError, ValueError):
            top_similarity = 0.0

        if top_similarity < CONFIANZA_MIN:
            await self._log(
                candidato,
                expediente_id=expediente_id,
                soportado=False,
                confianza=top_similarity,
                razonamiento=f"bajo_umbral (top_similarity={top_similarity:.3f})",
            )
            return None

        # Paso 3: aceptar. Extraemos cita + referencia canonica del chunk
        # top-1 y construimos el ArgumentoVerificado.
        cita_texto = str(best.get("text", "") or "")[:_MAX_CITA_VERIFICADA_CHARS]
        referencia = str(
            best.get("title") or best.get("source") or "sin_referencia"
        )

        # El rango de Pydantic para `confianza` es [0, 1]. Si por alguna
        # extraneza el retriever devuelve >1 (BM25 sin normalizar, p.ej.),
        # lo capamos a 1.0 — el log conserva el valor original.
        confianza_final = min(top_similarity, 1.0)

        await self._log(
            candidato,
            expediente_id=expediente_id,
            soportado=True,
            confianza=top_similarity,
            razonamiento="sobre_umbral",
        )

        return ArgumentoVerificado(
            regla_id=candidato.regla_id,
            descripcion=candidato.descripcion,
            cita_verificada=cita_texto,
            referencia_normativa_canonica=referencia,
            confianza=confianza_final,
            datos_disparo=candidato.datos_disparo,
            impacto_estimado=candidato.impacto_estimado,
        )

    # ------------------------------------------------------------------
    # Verificacion de una LISTA de candidatos
    # ------------------------------------------------------------------

    async def verify_all(
        self,
        candidatos: list[ArgumentoCandidato],
        *,
        expediente_id: Optional[str] = None,
        top_k: int = 5,
        territory_filter: Optional[str] = None,
    ) -> list[ArgumentoVerificado]:
        """Verifica una lista entera de candidatos.

        Los descartados por umbral, por error del retriever o por ausencia
        de resultados desaparecen silenciosamente de la salida. Esto implica
        que ``len(verify_all(cands)) <= len(cands)``, y que todo elemento
        de la salida cumple ``confianza >= CONFIANZA_MIN``.

        Args:
            candidatos: lista de ``ArgumentoCandidato`` producidos por el
                motor de reglas.
            expediente_id: id del expediente para trazabilidad en logs.
            top_k: ver ``verify_one``.
            territory_filter: ver ``verify_one``.

        Returns:
            Lista (posiblemente vacia) de ``ArgumentoVerificado`` que
            sobrevivieron al umbral. El orden respeta el orden de entrada.
        """
        verificados: list[ArgumentoVerificado] = []
        for candidato in candidatos:
            resultado = await self.verify_one(
                candidato,
                expediente_id=expediente_id,
                top_k=top_k,
                territory_filter=territory_filter,
            )
            if resultado is not None:
                verificados.append(resultado)
        return verificados

    # ------------------------------------------------------------------
    # Logging a defensia_rag_log
    # ------------------------------------------------------------------

    async def _log(
        self,
        candidato: ArgumentoCandidato,
        *,
        expediente_id: Optional[str],
        soportado: bool,
        confianza: float,
        razonamiento: str,
    ) -> None:
        """Inserta una fila en ``defensia_rag_log`` (best-effort).

        El log es una entrada de auditoria para poder ajustar reglas y
        umbrales en sesiones futuras. Si falla (Turso caido, esquema
        drift, etc.) el fallo se traga con warning: un problema de log
        jamas debe impedir que el verificador devuelva su resultado al
        motor de dictamenes.
        """
        if self.db is None:
            return

        # Columnas reales de la tabla segun migration 20260413:
        #   id, expediente_id, regla_id, soportado, confianza,
        #   razonamiento, created_at.
        sql = (
            "INSERT INTO defensia_rag_log "
            "(expediente_id, regla_id, soportado, confianza, razonamiento, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        # Guardamos tambien un prefijo de la cita propuesta dentro del
        # razonamiento para poder reconstruir el contexto del descarte sin
        # depender de la tabla `defensia_dictamenes`.
        cita_preview = (candidato.cita_normativa_propuesta or "")[:_MAX_CITA_LOG_CHARS]
        razonamiento_full = f"{razonamiento} | cita: {cita_preview}"

        params = [
            expediente_id or "",
            candidato.regla_id,
            1 if soportado else 0,
            float(confianza),
            razonamiento_full,
            datetime.now(timezone.utc).isoformat(),
        ]

        try:
            await self.db.execute(sql, params)
        except Exception as exc:
            # Fail-open: nunca propagar errores de logging al llamador.
            logger.warning(
                "RAG verifier: no se pudo loggear a defensia_rag_log "
                "(regla=%s, soportado=%s): %s",
                candidato.regla_id, soportado, exc,
            )


__all__ = ["CONFIANZA_MIN", "DefensiaRagVerifier"]
