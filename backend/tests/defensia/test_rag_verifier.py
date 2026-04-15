"""Tests del RAG verifier DefensIA (T2B-001 + T2B-002).

Estos tests aislan por completo al verificador del retriever real: el
`HybridRetriever` se mockea con `AsyncMock` y no se toca Upstash ni Turso.
El objetivo es comprobar el contrato anti-alucinacion:

1. `CONFIANZA_MIN = 0.7` es la constante dura del producto (decision B1).
2. Confianza estrictamente `< 0.7` se descarta en silencio (no aparece en
   el dictamen). Confianza `>= 0.7` se acepta y genera un
   `ArgumentoVerificado` con la cita canonica resuelta desde el RAG.
3. Cada verificacion (aceptada o descartada) se logea en la tabla
   `defensia_rag_log` para auditoria. El log es best-effort: un fallo de
   logging nunca debe tumbar el verificador.
4. `verify_all` es un simple filtro sobre `verify_one`: todo lo que
   sobrevive tiene confianza `>= 0.7`.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-001/002/003
Invariante #3 del plan v2 (umbral 0.7, no 0.6).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.defensia import ArgumentoCandidato, ArgumentoVerificado
from app.services.defensia_rag_verifier import (
    CONFIANZA_MIN,
    DefensiaRagVerifier,
)


# ---------------------------------------------------------------------------
# Helpers: factories para candidatos y resultados del retriever
# ---------------------------------------------------------------------------


def _make_candidato(
    regla_id: str = "R001",
    descripcion: str = "El acto carece de motivacion suficiente",
    cita: str = "Motivacion insuficiente del acto administrativo tributario",
    **datos_extra: Any,
) -> ArgumentoCandidato:
    """Construye un `ArgumentoCandidato` minimo valido."""
    return ArgumentoCandidato(
        regla_id=regla_id,
        descripcion=descripcion,
        cita_normativa_propuesta=cita,
        datos_disparo={"documento_id": "doc-1", **datos_extra},
        impacto_estimado="anulabilidad del acto",
    )


def _make_chunk(
    similarity: float,
    text: str = "Los actos administrativos tributarios deberan expresar los hechos y fundamentos de derecho (art. 102.2.c LGT).",
    title: str = "Ley General Tributaria — art. 102",
    source: str = "LGT",
    chunk_id: str = "chunk-1",
) -> dict[str, Any]:
    """Construye un dict con la forma que devuelve `HybridRetriever.search`."""
    return {
        "id": chunk_id,
        "text": text,
        "page": 42,
        "source": source,
        "title": title,
        "similarity": similarity,
        "territory": "AEAT",
        "tax_type": "",
    }


def _make_retriever(search_return: Any = None, search_side_effect: Any = None) -> MagicMock:
    """Construye un mock de `HybridRetriever` con `search` async configurable."""
    retriever = MagicMock()
    if search_side_effect is not None:
        retriever.search = AsyncMock(side_effect=search_side_effect)
    else:
        retriever.search = AsyncMock(return_value=search_return or [])
    return retriever


def _make_db() -> AsyncMock:
    """Mock de cliente Turso con `execute` asincrono."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(rows=[]))
    return db


# ---------------------------------------------------------------------------
# T2B-001 — verify_one / confianza / descartes / logs
# ---------------------------------------------------------------------------


async def test_verify_one_alta_confianza_devuelve_verificado():
    """Similarity 0.85 >> umbral — el argumento se acepta con la cita canonica."""
    retriever = _make_retriever(
        search_return=[
            _make_chunk(
                similarity=0.85,
                text="Art. 102.2.c LGT: los actos administrativos deberan expresar los hechos y los fundamentos de derecho.",
                title="LGT art. 102",
            )
        ]
    )
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    candidato = _make_candidato()
    resultado = await verifier.verify_one(candidato)

    assert isinstance(resultado, ArgumentoVerificado)
    assert resultado.regla_id == "R001"
    assert resultado.confianza == pytest.approx(0.85)
    assert resultado.referencia_normativa_canonica == "LGT art. 102"
    assert "102.2.c LGT" in resultado.cita_verificada
    assert resultado.datos_disparo == candidato.datos_disparo
    assert resultado.impacto_estimado == candidato.impacto_estimado
    retriever.search.assert_awaited_once()


async def test_verify_one_baja_confianza_descarta():
    """Similarity 0.65 < 0.7 — descartado silenciosamente, retorna None."""
    retriever = _make_retriever(search_return=[_make_chunk(similarity=0.65)])
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    resultado = await verifier.verify_one(_make_candidato())

    assert resultado is None


async def test_verify_one_umbral_exacto():
    """La frontera exacta del umbral — 0.70 acepta, 0.69 descarta.

    Comprobamos ambos lados del corte en el mismo test para atar de forma
    explicita el criterio `>= 0.7` (no `>`).
    """
    # Borde inferior aceptado: 0.70 exacto.
    retriever_ok = _make_retriever(search_return=[_make_chunk(similarity=0.70)])
    verifier_ok = DefensiaRagVerifier(retriever=retriever_ok, db_client=_make_db())
    aceptado = await verifier_ok.verify_one(_make_candidato())
    assert aceptado is not None, "confianza=0.70 debe aceptarse (criterio >= 0.7)"
    assert aceptado.confianza == pytest.approx(0.70)

    # Justo por debajo: 0.69 se descarta.
    retriever_ko = _make_retriever(search_return=[_make_chunk(similarity=0.69)])
    verifier_ko = DefensiaRagVerifier(retriever=retriever_ko, db_client=_make_db())
    descartado = await verifier_ko.verify_one(_make_candidato())
    assert descartado is None, "confianza=0.69 debe descartarse (estrictamente < 0.7)"


async def test_verify_one_sin_resultados_retriever():
    """Si el retriever no devuelve nada, el candidato se descarta y se logea."""
    retriever = _make_retriever(search_return=[])
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    resultado = await verifier.verify_one(_make_candidato())

    assert resultado is None
    # Se llamo a execute al menos una vez para loggear el descarte.
    assert db.execute.await_count >= 1
    call_args = db.execute.await_args_list[0]
    sql = call_args.args[0]
    params = call_args.args[1]
    assert "defensia_rag_log" in sql
    assert "INSERT" in sql.upper()
    # La razon del descarte debe indicar "sin_resultados" en algun parametro.
    assert any("sin_resultados" in str(p) for p in params)


async def test_verify_one_error_retriever_no_tumba_pipeline():
    """Si el retriever lanza excepcion, el verificador devuelve None y logea."""
    retriever = _make_retriever(search_side_effect=RuntimeError("upstash caido"))
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    resultado = await verifier.verify_one(_make_candidato())

    assert resultado is None
    assert db.execute.await_count >= 1
    params = db.execute.await_args_list[0].args[1]
    joined = " ".join(str(p) for p in params)
    assert "retriever_error" in joined
    assert "upstash caido" in joined


async def test_verify_all_filtra_descartes_silenciosamente():
    """3 candidatos con similarities [0.85, 0.65, 0.10] — solo sobrevive 1."""
    candidatos = [
        _make_candidato(regla_id="R001"),
        _make_candidato(regla_id="R005"),
        _make_candidato(regla_id="R999"),
    ]
    chunks_por_candidato = [
        [_make_chunk(similarity=0.85, chunk_id="c1")],
        [_make_chunk(similarity=0.65, chunk_id="c2")],
        [_make_chunk(similarity=0.10, chunk_id="c3")],
    ]
    # El mock se llama 3 veces — devolvemos un set distinto en cada llamada.
    retriever = _make_retriever(search_side_effect=chunks_por_candidato)
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=_make_db())

    verificados = await verifier.verify_all(candidatos)

    assert len(verificados) == 1, "Solo R001 (0.85) debe sobrevivir al umbral 0.7"
    assert verificados[0].regla_id == "R001"
    assert retriever.search.await_count == 3


async def test_verify_all_invariante_todos_sobre_umbral():
    """Invariante dura: cada argumento retornado cumple `confianza >= 0.7`."""
    candidatos = [
        _make_candidato(regla_id="R001"),
        _make_candidato(regla_id="R002"),
        _make_candidato(regla_id="R003"),
        _make_candidato(regla_id="R004"),
    ]
    # Mezcla sobre y bajo el umbral.
    chunks = [
        [_make_chunk(similarity=0.92, chunk_id="c1")],
        [_make_chunk(similarity=0.71, chunk_id="c2")],
        [_make_chunk(similarity=0.50, chunk_id="c3")],
        [_make_chunk(similarity=0.70, chunk_id="c4")],
    ]
    retriever = _make_retriever(search_side_effect=chunks)
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=_make_db())

    verificados = await verifier.verify_all(candidatos)

    assert all(a.confianza >= CONFIANZA_MIN for a in verificados)
    assert {a.regla_id for a in verificados} == {"R001", "R002", "R004"}


async def test_confianza_min_constante_es_07():
    """La constante exportada debe ser exactamente 0.7 — invariante #3 del plan v2."""
    assert CONFIANZA_MIN == 0.7


async def test_log_descarte_llama_db_con_decision_descartada():
    """Un descarte por umbral debe loggear una fila con soportado=0 en defensia_rag_log."""
    retriever = _make_retriever(search_return=[_make_chunk(similarity=0.40)])
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    await verifier.verify_one(_make_candidato(regla_id="R042"))

    assert db.execute.await_count >= 1
    call = db.execute.await_args_list[0]
    sql = call.args[0]
    params = call.args[1]
    assert "INSERT INTO defensia_rag_log" in sql
    # Debe incluir la columna `soportado` y un valor 0 para descartado.
    assert "soportado" in sql
    assert 0 in params, "soportado=0 debe aparecer en los parametros del INSERT"
    assert "R042" in params


async def test_log_aceptado_llama_db_con_decision_aceptada():
    """Un aceptado debe loggear una fila con soportado=1."""
    retriever = _make_retriever(search_return=[_make_chunk(similarity=0.91)])
    db = _make_db()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    resultado = await verifier.verify_one(_make_candidato(regla_id="R011"))

    assert resultado is not None
    assert db.execute.await_count >= 1
    call = db.execute.await_args_list[0]
    sql = call.args[0]
    params = call.args[1]
    assert "INSERT INTO defensia_rag_log" in sql
    assert 1 in params, "soportado=1 debe aparecer en los parametros del INSERT"
    assert "R011" in params


async def test_log_fallo_no_rompe_verificacion():
    """Si el log falla, el verificador sigue devolviendo el resultado correcto."""
    retriever = _make_retriever(search_return=[_make_chunk(similarity=0.95)])
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("turso caido"))
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=db)

    resultado = await verifier.verify_one(_make_candidato())

    # El error de logging se traga y el resultado sigue siendo valido.
    assert resultado is not None
    assert resultado.confianza == pytest.approx(0.95)


async def test_db_none_modo_silencioso():
    """Un verificador sin db_client funciona sin logs (modo test ligero)."""
    retriever = _make_retriever(search_return=[_make_chunk(similarity=0.99)])
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=None)

    resultado = await verifier.verify_one(_make_candidato())

    assert resultado is not None
    assert resultado.confianza == pytest.approx(0.99)
