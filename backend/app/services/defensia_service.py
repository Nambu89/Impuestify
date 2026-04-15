"""DefensIA Service Facade (T2B-009).

Orquesta el pipeline completo del analisis de un expediente:

    reserve cuota
        -> (detect_fase si el expediente viene INDETERMINADO)
        -> defensia_rules_engine.evaluar
        -> rag_verifier.verify_all
        -> writer_service.render_escrito + writer_service.render_dictamen
        -> persistir dictamen + escrito en Turso
        -> commit cuota

Es el unico entry point que los endpoints REST de `/api/defensia/*` deberian
llamar. La fachada NO ejecuta el analisis juridico hasta que recibe un brief
no nulo del usuario (Regla #1 del producto DefensIA): la Fase 1 de extraccion
tecnica que ocurre al subir documentos vive fuera de este facade, en el
router de upload.

Reserve-commit-release
----------------------
El patron es identico al del `DefensiaQuotaService`:

- `reserve()` se hace ANTES de cualquier trabajo caro. Si levanta
  ``QuotaExcedida`` la excepcion se propaga sin tocar `release()`, porque
  la reserva nunca llego a crearse.
- Si cualquier paso posterior falla, el facade llama `release()` en un
  bloque `except` generico para devolver la plaza al usuario.
- Solo tras persistir dictamen y escrito con exito se llama `commit()`.

Persistencia y esquema real
---------------------------
Los INSERTs apuntan al esquema fisico definido en
`20260413_defensia_tables.sql`, NO al esquema hipotetico del plan v2:

- `defensia_dictamenes` -> columnas:
    id, expediente_id, brief_id, fase_detectada, argumentos_json,
    resumen_caso, created_at, modelo_llm, tokens_consumidos.
  Usamos `resumen_caso` (NO `resumen_markdown`) y guardamos el markdown
  del dictamen ahi. `brief_id` y `tokens_consumidos` quedan NULL en v1
  porque el brief se persiste aparte y el writer aun no expone el conteo
  de tokens.
- `defensia_escritos` -> columnas:
    id, expediente_id, dictamen_id, tipo_escrito, contenido_markdown,
    version, editado_por_usuario, created_at, updated_at.
  Insertamos version=1 y editado_por_usuario=0 para la primera escritura;
  `tipo_escrito` se deriva de la fase detectada.

Invariantes de test (test_defensia_service.py)
----------------------------------------------
- El orden del pipeline es determinista y verificable via mocks.
- `argumentos_descartados_count = len(candidatos) - len(verificados)`.
- `detect_fase` solo se llama si `expediente.fase_detectada == Fase.INDETERMINADA`.
- Los SQL usan placeholders `?` parametrizados (nunca f-strings con datos).
- Las ids generadas son prefijadas: `dict_` para dictamenes y `esc_` para
  escritos, para que el router las pueda usar en rutas `/api/defensia/<id>`.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-009
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.defensia import (
    ArgumentoCandidato,
    ArgumentoVerificado,
    Brief,
    ExpedienteEstructurado,
    Fase,
)

logger = logging.getLogger(__name__)


# Mapping fase -> tipo_escrito persistido. El writer ya hace una seleccion
# analoga para elegir plantilla, pero aqui queremos un valor estable y
# Campos que pueden contener el importe economico relevante para decidir
# entre TEAR abreviada (<6000 EUR) y general (>=6000 EUR) segun art. 245 LGT.
# Revisamos estos campos en los documentos estructurados y tomamos el maximo.
_CAMPOS_CUOTA_CANDIDATOS: tuple[str, ...] = (
    "cuota",
    "cuota_propuesta",
    "cuota_tributaria",
    "importe_sancion",
    "importe_total",
    "total_a_ingresar",
)


def _extraer_cuota_maxima(expediente: ExpedienteEstructurado) -> float:
    """Recorre los documentos estructurados y devuelve el importe maximo
    encontrado en los campos canonicos de cuota tributaria / sancion.

    Se usa para que el writer seleccione la plantilla TEAR correcta. Si no
    hay ningun importe encontrado devuelve 0.0 — el writer cae al fallback
    abreviada (que es el caso mas comun y mas favorable al usuario).
    """
    maximo = 0.0
    for doc in expediente.documentos:
        datos = getattr(doc, "datos", None) or {}
        if not isinstance(datos, dict):
            continue
        for campo in _CAMPOS_CUOTA_CANDIDATOS:
            val = datos.get(campo)
            if val is None:
                continue
            try:
                val_f = float(val)
            except (TypeError, ValueError):
                continue
            if val_f > maximo:
                maximo = val_f
    return maximo


# compacto para la columna `tipo_escrito` de `defensia_escritos` sin
# acoplarnos al nombre del fichero Jinja.
_TIPO_ESCRITO_POR_FASE: dict[Fase, str] = {
    Fase.COMPROBACION_REQUERIMIENTO: "alegaciones_verificacion",
    Fase.COMPROBACION_PROPUESTA: "alegaciones_verificacion",
    Fase.COMPROBACION_POST_ALEGACIONES: "alegaciones_comprobacion_limitada",
    Fase.LIQUIDACION_FIRME_PLAZO_RECURSO: "recurso_reposicion",
    Fase.SANCIONADOR_INICIADO: "alegaciones_sancionador",
    Fase.SANCIONADOR_PROPUESTA: "alegaciones_sancionador",
    Fase.SANCIONADOR_IMPUESTA: "alegaciones_sancionador",
    Fase.REPOSICION_INTERPUESTA: "reclamacion_tear",
    Fase.TEAR_INTERPUESTA: "ampliacion_tear",
    Fase.TEAR_AMPLIACION_POSIBLE: "ampliacion_tear",
}


class DefensiaService:
    """Facade que orquesta el pipeline completo de analisis DefensIA."""

    def __init__(
        self,
        *,
        db_client: Any,
        rag_verifier: Any,
        quota_service: Any,
        writer_service: Any,
        export_service: Any,
        storage: Any = None,
    ) -> None:
        self.db = db_client
        self.rag_verifier = rag_verifier
        self.quota_service = quota_service
        self.writer = writer_service
        self.exporter = export_service
        self.storage = storage

    # ------------------------------------------------------------------ #
    # Entry point principal — analizar un expediente completo
    # ------------------------------------------------------------------ #

    async def analizar_expediente(
        self,
        expediente: ExpedienteEstructurado,
        brief: Brief,
        *,
        user_id: str,
        plan: str,
        territory_filter: Optional[str] = None,
    ) -> dict:
        """Pipeline completo con reserve-commit-release de cuota.

        Args:
            expediente: expediente ya estructurado (documentos clasificados +
                datos extraidos). Si ``fase_detectada == INDETERMINADA`` la
                fachada la auto-detecta antes de seguir.
            brief: brief del usuario, obligatorio por la Regla #1 del producto
                (el analisis no arranca sin intencion explicita).
            user_id: id del usuario para gestion de cuota.
            plan: plan de suscripcion (`particular`, `autonomo`, `creator`).
            territory_filter: filtro opcional de territorio que se propaga al
                RAG verifier para refinar las citas canonicas.

        Returns:
            dict con claves:
              - ``escrito_markdown``: markdown renderizado del escrito principal.
              - ``dictamen_markdown``: markdown del dictamen interno.
              - ``argumentos_verificados``: ``list[ArgumentoVerificado]``.
              - ``argumentos_descartados_count``: int, cuantos candidatos
                fueron descartados por el RAG verifier.
              - ``reserva_id``: token opaco de la reserva de cuota.
              - ``dictamen_id``: id prefijado `dict_...` del dictamen insertado.
              - ``escrito_id``: id prefijado `esc_...` del escrito insertado.
              - ``expediente_id``: eco del id del expediente.
              - ``fase_detectada``: string con el ``Fase`` detectada (tras
                eventual auto-deteccion).

        Raises:
            QuotaExcedida: si el usuario ha agotado su cuota mensual.
            RuntimeError / Exception: cualquier fallo aguas abajo. En caso
                de fallo post-reserve, la fachada llama `release()` antes
                de re-lanzar para no consumir cuota al usuario.
        """
        # 1. Reserva de cuota. Puede levantar QuotaExcedida — en ese caso
        #    NO debemos llamar a release() porque la reserva nunca se creo.
        reserva_id = await self.quota_service.reserve(user_id, plan)

        try:
            # 2. Phase detection: solo si el expediente viene INDETERMINADO.
            #    Evitamos re-detectar expedientes ya clasificados para no
            #    sobreescribir decisiones manuales del usuario en el futuro.
            if expediente.fase_detectada == Fase.INDETERMINADA:
                from app.services.defensia_phase_detector import detect_fase

                nueva_fase, confianza = detect_fase(expediente)
                expediente.fase_detectada = nueva_fase
                expediente.fase_confianza = confianza
                logger.info(
                    "DefensIA: fase auto-detectada para %s -> %s (%.2f)",
                    expediente.id, nueva_fase.value, confianza,
                )

            # 3. Rules engine -> lista de candidatos deterministas.
            from app.services import defensia_rules
            from app.services.defensia_rules_engine import evaluar as evaluar_reglas

            defensia_rules.load_all()
            candidatos: list[ArgumentoCandidato] = evaluar_reglas(expediente, brief)
            logger.info(
                "DefensIA analisis: expediente=%s fase=%s candidatos=%d",
                expediente.id,
                (
                    expediente.fase_detectada.value
                    if hasattr(expediente.fase_detectada, "value")
                    else str(expediente.fase_detectada)
                ),
                len(candidatos),
            )

            # 4. RAG verifier -> solo los que superan umbral 0.7.
            #    El verifier loggea a defensia_rag_log internamente.
            verificados: list[ArgumentoVerificado] = await self.rag_verifier.verify_all(
                candidatos,
                expediente_id=expediente.id,
                territory_filter=territory_filter,
            )
            descartados = max(0, len(candidatos) - len(verificados))

            # 5. Writer: render escrito + dictamen. El writer es sincrono;
            #    la lentitud aqui viene de Jinja que es CPU-bound, no I/O.
            #    `cuota_estimada_eur` se extrae del maximo importe encontrado
            #    en los documentos estructurados del expediente (propuesta de
            #    liquidacion, liquidacion provisional, acuerdo de sancion).
            #    El writer usa ese valor para decidir entre TEAR abreviada
            #    (<6000 EUR) o general (>=6000 EUR) segun art. 245 LGT.
            cuota_estimada = _extraer_cuota_maxima(expediente)
            escrito_md: str = self.writer.render_escrito(
                expediente,
                verificados,
                brief,
                cuota_estimada_eur=cuota_estimada,
            )
            dictamen_md: str = self.writer.render_dictamen(
                expediente, verificados, brief
            )

            # 6. Persistir dictamen PRIMERO (el escrito lo referencia por FK).
            dictamen_id = await self._persistir_dictamen(
                expediente=expediente,
                dictamen_md=dictamen_md,
                verificados=verificados,
            )
            escrito_id = await self._persistir_escrito(
                expediente=expediente,
                dictamen_id=dictamen_id,
                contenido_md=escrito_md,
            )

            # 7. Commit cuota solo tras persistencia exitosa.
            await self.quota_service.commit(user_id, reserva_id)

            return {
                "escrito_markdown": escrito_md,
                "dictamen_markdown": dictamen_md,
                "argumentos_verificados": verificados,
                "argumentos_descartados_count": descartados,
                "reserva_id": reserva_id,
                "dictamen_id": dictamen_id,
                "escrito_id": escrito_id,
                "expediente_id": expediente.id,
                "fase_detectada": (
                    expediente.fase_detectada.value
                    if hasattr(expediente.fase_detectada, "value")
                    else str(expediente.fase_detectada)
                ),
            }

        except Exception:
            # Release cuota en cualquier fallo post-reserve — no penalizamos
            # al usuario por errores del sistema (Turso caido, writer roto,
            # regla con bug, etc.). El release es best-effort: si fallase
            # tambien propagamos el error original.
            try:
                await self.quota_service.release(user_id, reserva_id)
            except Exception as release_exc:  # pragma: no cover — defensa
                logger.error(
                    "DefensIA: release de cuota fallo tras error en analisis: %s",
                    release_exc,
                )
            raise

    # ------------------------------------------------------------------ #
    # Persistencia — SQL parametrizado contra esquema real
    # ------------------------------------------------------------------ #

    async def _persistir_dictamen(
        self,
        *,
        expediente: ExpedienteEstructurado,
        dictamen_md: str,
        verificados: list[ArgumentoVerificado],
    ) -> str:
        """Inserta una fila en ``defensia_dictamenes`` y devuelve el id generado.

        Columnas reales segun ``20260413_defensia_tables.sql``:

            id, expediente_id, brief_id, fase_detectada, argumentos_json,
            resumen_caso, created_at, modelo_llm, tokens_consumidos

        En v1:

        - ``brief_id`` se deja NULL (el brief se persiste aparte en el router
          de upload del brief — ver plan T2B-018).
        - ``modelo_llm`` se fuerza a `gpt-5-mini` como default del backend.
        - ``tokens_consumidos`` queda NULL hasta que el writer exponga conteo.
        """
        dictamen_id = f"dict_{secrets.token_urlsafe(12)}"
        fase_str = (
            expediente.fase_detectada.value
            if hasattr(expediente.fase_detectada, "value")
            else str(expediente.fase_detectada)
        )
        argumentos_json = json.dumps(
            [v.model_dump() for v in verificados],
            ensure_ascii=False,
            default=str,
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        sql = (
            "INSERT INTO defensia_dictamenes "
            "(id, expediente_id, brief_id, fase_detectada, argumentos_json, "
            "resumen_caso, created_at, modelo_llm, tokens_consumidos) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            dictamen_id,
            expediente.id,
            None,            # brief_id (v1: no enlazado)
            fase_str,
            argumentos_json,
            dictamen_md,     # resumen_caso: guardamos markdown del dictamen
            now_iso,
            "gpt-5-mini",    # modelo_llm (default backend)
            None,            # tokens_consumidos (v1: pendiente)
        ]
        await self.db.execute(sql, params)
        logger.info(
            "DefensIA: dictamen persistido id=%s expediente=%s argumentos=%d",
            dictamen_id, expediente.id, len(verificados),
        )
        return dictamen_id

    async def _persistir_escrito(
        self,
        *,
        expediente: ExpedienteEstructurado,
        dictamen_id: str,
        contenido_md: str,
    ) -> str:
        """Inserta una fila en ``defensia_escritos`` y devuelve el id generado.

        Columnas reales segun ``20260413_defensia_tables.sql``:

            id, expediente_id, dictamen_id, tipo_escrito, contenido_markdown,
            version, editado_por_usuario, created_at, updated_at

        Insertamos siempre ``version=1`` y ``editado_por_usuario=0`` para la
        primera escritura. El PATCH de edicion de contenido (T2B-015b) se
        encargara de incrementar la version y marcar el flag.
        """
        escrito_id = f"esc_{secrets.token_urlsafe(12)}"
        tipo_escrito = _TIPO_ESCRITO_POR_FASE.get(
            expediente.fase_detectada, "alegaciones_generico"
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        sql = (
            "INSERT INTO defensia_escritos "
            "(id, expediente_id, dictamen_id, tipo_escrito, contenido_markdown, "
            "version, editado_por_usuario, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            escrito_id,
            expediente.id,
            dictamen_id,
            tipo_escrito,
            contenido_md,
            1,     # version inicial
            0,     # editado_por_usuario: false en la primera escritura
            now_iso,
            now_iso,
        ]
        await self.db.execute(sql, params)
        logger.info(
            "DefensIA: escrito persistido id=%s tipo=%s expediente=%s",
            escrito_id, tipo_escrito, expediente.id,
        )
        return escrito_id


__all__ = ["DefensiaService"]
