"""Tests T2B-009 — DefensIA Service Facade (orquestador del pipeline).

El service facade orquesta el pipeline completo de analisis de un expediente:

    reserve cuota -> (detect_fase si hace falta) -> rules_engine.evaluar
    -> rag_verifier.verify_all -> writer.render_escrito + writer.render_dictamen
    -> persistir dictamen y escrito -> commit cuota

Si cualquier paso falla, la reserva de cuota se libera via `release()` para
no penalizar al usuario. Si la propia reserva falla (cuota agotada), la
excepcion se propaga sin tocar `release()` porque nunca llego a reservarse.

Estos tests usan mocks para todos los componentes (el service es una
fachada "integration light") y verifican:

1. El orden del pipeline.
2. La correcta gestion reserve/commit/release.
3. Los SQL de persistencia contra el esquema real (20260413_defensia_tables.sql),
   NO contra un esquema hipotetico del plan.
4. El conteo de argumentos descartados por el RAG verifier.
5. La deteccion de fase automatica solo cuando `fase_detectada == INDETERMINADA`.

Invariantes
-----------
- `defensia_dictamenes` usa la columna `resumen_caso` (NO `resumen_markdown`).
- `defensia_dictamenes` requiere `fase_detectada` y `modelo_llm`.
- `defensia_escritos` requiere `dictamen_id`, `tipo_escrito`, `version=1`,
  `editado_por_usuario=0`, `created_at`, `updated_at`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from typing import Any

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    ArgumentoVerificado,
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_quota_service import QuotaExcedida
from app.services.defensia_service import DefensiaService


# --------------------------------------------------------------------------- #
# Fake async DB — solo registra las llamadas para poder auditar el SQL
# --------------------------------------------------------------------------- #


class FakeDB:
    """Fake async db client que registra (sql, params) en cada execute."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list]] = []
        self.should_fail: bool = False

    async def execute(self, sql: str, params: list | None = None):
        self.calls.append((sql, list(params or [])))
        if self.should_fail:
            raise RuntimeError("db explotado en test")

        class _Result:
            rows: list = []

        return _Result()


# --------------------------------------------------------------------------- #
# Fixtures de dominio
# --------------------------------------------------------------------------- #


@pytest.fixture
def expediente_con_fase() -> ExpedienteEstructurado:
    """Expediente con fase ya detectada (no re-detecta)."""
    doc = DocumentoEstructurado(
        id="doc_1",
        nombre_original="liquidacion.pdf",
        tipo_documento=TipoDocumento.LIQUIDACION_PROVISIONAL,
        fecha_acto=datetime(2026, 3, 1, tzinfo=timezone.utc),
        datos={},
    )
    return ExpedienteEstructurado(
        id="exp_test_001",
        tributo=Tributo.IRPF,
        ccaa="Madrid",
        documentos=[doc],
        fase_detectada=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        fase_confianza=0.9,
    )


@pytest.fixture
def expediente_sin_fase() -> ExpedienteEstructurado:
    """Expediente con fase INDETERMINADA -> el facade debe auto-detectar."""
    doc = DocumentoEstructurado(
        id="doc_1",
        nombre_original="req.pdf",
        tipo_documento=TipoDocumento.REQUERIMIENTO,
        fecha_acto=datetime(2026, 3, 1, tzinfo=timezone.utc),
        datos={},
    )
    return ExpedienteEstructurado(
        id="exp_test_002",
        tributo=Tributo.IRPF,
        ccaa="Madrid",
        documentos=[doc],
        fase_detectada=Fase.INDETERMINADA,
        fase_confianza=0.0,
    )


@pytest.fixture
def brief_valido() -> Brief:
    return Brief(
        texto="Me han denegado gastos de suministros sin motivacion real.",
        chat_history=[],
    )


def _candidato(regla_id: str) -> ArgumentoCandidato:
    return ArgumentoCandidato(
        regla_id=regla_id,
        descripcion=f"Descripcion {regla_id}",
        cita_normativa_propuesta=f"Cita propuesta de {regla_id}",
        datos_disparo={"foo": "bar"},
        impacto_estimado="medio",
    )


def _verificado(regla_id: str) -> ArgumentoVerificado:
    return ArgumentoVerificado(
        regla_id=regla_id,
        descripcion=f"Descripcion {regla_id}",
        cita_verificada=f"Texto verificado de {regla_id}",
        referencia_normativa_canonica="Art. 102.2.c LGT",
        confianza=0.85,
        datos_disparo={"foo": "bar"},
        impacto_estimado="medio",
    )


def _build_service_with_mocks(
    *,
    db: FakeDB,
    candidatos: list[ArgumentoCandidato] | None = None,
    verificados: list[ArgumentoVerificado] | None = None,
    escrito_md: str = "# Escrito markdown",
    dictamen_md: str = "# Dictamen markdown",
) -> tuple[DefensiaService, dict[str, Any]]:
    """Construye un DefensiaService con mocks fully wired.

    Devuelve (service, mocks) para poder hacer asserts sobre los mocks
    fuera de este helper.
    """
    rag_verifier = MagicMock()
    rag_verifier.verify_all = AsyncMock(return_value=verificados or [])

    quota_service = MagicMock()
    quota_service.reserve = AsyncMock(return_value="res_fake_123")
    quota_service.commit = AsyncMock(return_value=None)
    quota_service.release = AsyncMock(return_value=None)

    writer_service = MagicMock()
    writer_service.render_escrito = MagicMock(return_value=escrito_md)
    writer_service.render_dictamen = MagicMock(return_value=dictamen_md)

    export_service = MagicMock()

    service = DefensiaService(
        db_client=db,
        rag_verifier=rag_verifier,
        quota_service=quota_service,
        writer_service=writer_service,
        export_service=export_service,
    )
    mocks = {
        "rag_verifier": rag_verifier,
        "quota_service": quota_service,
        "writer_service": writer_service,
        "export_service": export_service,
        "candidatos": candidatos or [],
    }
    return service, mocks


# --------------------------------------------------------------------------- #
# Test 1 — Happy path, pipeline order + dict de retorno
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_pipeline_completo_happy_path(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [_candidato("R001"), _candidato("R002")]
    verificados = [_verificado("R001"), _verificado("R002")]
    service, mocks = _build_service_with_mocks(
        db=db,
        candidatos=candidatos,
        verificados=verificados,
    )

    # Parcheamos el rules engine para devolver `candidatos`.
    call_order: list[str] = []

    def _fake_evaluar(exp, brief):
        call_order.append("evaluar")
        return candidatos

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", _fake_evaluar
    )
    monkeypatch.setattr(
        "app.services.defensia_rules.load_all", lambda: call_order.append("load_all")
    )

    # Tambien envolvemos los mocks async para registrar el orden.
    original_reserve = mocks["quota_service"].reserve
    async def tracked_reserve(*a, **kw):
        call_order.append("reserve")
        return await original_reserve(*a, **kw)
    mocks["quota_service"].reserve = tracked_reserve

    original_verify = mocks["rag_verifier"].verify_all
    async def tracked_verify(*a, **kw):
        call_order.append("verify_all")
        return await original_verify(*a, **kw)
    mocks["rag_verifier"].verify_all = tracked_verify

    original_render_escrito = mocks["writer_service"].render_escrito
    def tracked_render_escrito(*a, **kw):
        call_order.append("render_escrito")
        return original_render_escrito(*a, **kw)
    mocks["writer_service"].render_escrito = tracked_render_escrito

    original_render_dictamen = mocks["writer_service"].render_dictamen
    def tracked_render_dictamen(*a, **kw):
        call_order.append("render_dictamen")
        return original_render_dictamen(*a, **kw)
    mocks["writer_service"].render_dictamen = tracked_render_dictamen

    original_commit = mocks["quota_service"].commit
    async def tracked_commit(*a, **kw):
        call_order.append("commit")
        return await original_commit(*a, **kw)
    mocks["quota_service"].commit = tracked_commit

    result = await service.analizar_expediente(
        expediente_con_fase,
        brief_valido,
        user_id="user_123",
        plan="autonomo",
    )

    # Orden esperado: reserve -> evaluar -> verify_all -> render_escrito
    # -> render_dictamen -> commit. `load_all` aparece antes de evaluar.
    assert call_order.index("reserve") < call_order.index("evaluar")
    assert call_order.index("evaluar") < call_order.index("verify_all")
    assert call_order.index("verify_all") < call_order.index("render_escrito")
    assert call_order.index("render_escrito") < call_order.index("render_dictamen")
    assert call_order.index("render_dictamen") < call_order.index("commit")

    # Dict de retorno con todas las claves documentadas.
    assert set(result.keys()) >= {
        "escrito_markdown",
        "dictamen_markdown",
        "argumentos_verificados",
        "argumentos_descartados_count",
        "reserva_id",
        "dictamen_id",
        "escrito_id",
        "expediente_id",
        "fase_detectada",
    }
    assert result["escrito_markdown"] == "# Escrito markdown"
    assert result["dictamen_markdown"] == "# Dictamen markdown"
    assert result["argumentos_verificados"] == verificados
    assert result["argumentos_descartados_count"] == 0
    assert result["reserva_id"] == "res_fake_123"
    assert result["expediente_id"] == "exp_test_001"
    assert result["fase_detectada"] == Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value


# --------------------------------------------------------------------------- #
# Test 2 — release on rules_engine.evaluar error
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_release_on_rules_error(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    service, mocks = _build_service_with_mocks(db=db)

    def _boom(exp, brief):
        raise RuntimeError("rules explotaron")

    monkeypatch.setattr("app.services.defensia_rules_engine.evaluar", _boom)
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    with pytest.raises(RuntimeError, match="rules explotaron"):
        await service.analizar_expediente(
            expediente_con_fase,
            brief_valido,
            user_id="user_123",
            plan="autonomo",
        )

    mocks["quota_service"].reserve.assert_awaited_once()
    mocks["quota_service"].release.assert_awaited_once()
    mocks["quota_service"].commit.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Test 3 — release on rag_verifier.verify_all error
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_release_on_verify_error(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [_candidato("R001")]
    service, mocks = _build_service_with_mocks(db=db, candidatos=candidatos)

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    mocks["rag_verifier"].verify_all = AsyncMock(
        side_effect=RuntimeError("rag caido")
    )

    with pytest.raises(RuntimeError, match="rag caido"):
        await service.analizar_expediente(
            expediente_con_fase,
            brief_valido,
            user_id="user_123",
            plan="autonomo",
        )

    mocks["quota_service"].release.assert_awaited_once()
    mocks["quota_service"].commit.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Test 4 — release on writer.render_escrito error
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_release_on_writer_error(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [_candidato("R001")]
    verificados = [_verificado("R001")]
    service, mocks = _build_service_with_mocks(
        db=db, candidatos=candidatos, verificados=verificados
    )

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    mocks["writer_service"].render_escrito = MagicMock(
        side_effect=RuntimeError("writer fail")
    )

    with pytest.raises(RuntimeError, match="writer fail"):
        await service.analizar_expediente(
            expediente_con_fase,
            brief_valido,
            user_id="user_123",
            plan="autonomo",
        )

    mocks["quota_service"].release.assert_awaited_once()
    mocks["quota_service"].commit.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Test 5 — release on db persistence error
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_release_on_db_error(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    db.should_fail = True  # todas las execute revientan

    candidatos = [_candidato("R001")]
    verificados = [_verificado("R001")]
    service, mocks = _build_service_with_mocks(
        db=db, candidatos=candidatos, verificados=verificados
    )

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    with pytest.raises(RuntimeError, match="db explotado en test"):
        await service.analizar_expediente(
            expediente_con_fase,
            brief_valido,
            user_id="user_123",
            plan="autonomo",
        )

    mocks["quota_service"].release.assert_awaited_once()
    mocks["quota_service"].commit.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Test 6 — QuotaExcedida se propaga y release NO se llama
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_quota_excedida_propaga(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    service, mocks = _build_service_with_mocks(db=db)
    mocks["quota_service"].reserve = AsyncMock(
        side_effect=QuotaExcedida("cuota agotada")
    )

    # Parcheos para evitar import side-effects aunque el test no llegue
    # tan lejos.
    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: []
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    with pytest.raises(QuotaExcedida, match="cuota agotada"):
        await service.analizar_expediente(
            expediente_con_fase,
            brief_valido,
            user_id="user_123",
            plan="particular",
        )

    # Nunca se reservo -> nunca release, nunca commit.
    mocks["quota_service"].release.assert_not_awaited()
    mocks["quota_service"].commit.assert_not_awaited()
    mocks["rag_verifier"].verify_all.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Test 7 — Argumentos descartados se contabilizan bien
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_descarte_argumentos_contabilizado(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [
        _candidato("R001"),
        _candidato("R002"),
        _candidato("R003"),
        _candidato("R004"),
        _candidato("R005"),
    ]
    verificados = [
        _verificado("R001"),
        _verificado("R003"),
        _verificado("R005"),
    ]
    service, mocks = _build_service_with_mocks(
        db=db, candidatos=candidatos, verificados=verificados
    )

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    result = await service.analizar_expediente(
        expediente_con_fase,
        brief_valido,
        user_id="user_123",
        plan="autonomo",
    )

    assert result["argumentos_descartados_count"] == 2
    assert len(result["argumentos_verificados"]) == 3


# --------------------------------------------------------------------------- #
# Test 8 — Phase detection automatica cuando fase=INDETERMINADA
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_phase_detection_auto_si_indeterminada(
    monkeypatch, expediente_sin_fase, expediente_con_fase, brief_valido
):
    db = FakeDB()
    service, mocks = _build_service_with_mocks(db=db)

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: []
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    detect_calls: list[str] = []

    def _fake_detect(expediente, hoy=None):
        detect_calls.append(expediente.id)
        return (Fase.COMPROBACION_REQUERIMIENTO, 0.95)

    monkeypatch.setattr(
        "app.services.defensia_phase_detector.detect_fase", _fake_detect
    )

    # Caso A: fase INDETERMINADA -> llama detect_fase y actualiza el expediente
    result_a = await service.analizar_expediente(
        expediente_sin_fase,
        brief_valido,
        user_id="user_1",
        plan="autonomo",
    )
    assert detect_calls == ["exp_test_002"]
    assert result_a["fase_detectada"] == Fase.COMPROBACION_REQUERIMIENTO.value

    # Caso B: fase ya detectada -> NO re-detecta
    result_b = await service.analizar_expediente(
        expediente_con_fase,
        brief_valido,
        user_id="user_1",
        plan="autonomo",
    )
    # detect_calls no cambia (sigue siendo 1 llamada del caso A)
    assert detect_calls == ["exp_test_002"]
    assert result_b["fase_detectada"] == Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value


# --------------------------------------------------------------------------- #
# Test 9 — SQL INSERT en defensia_dictamenes contra esquema real
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_persiste_dictamen_con_sql_correcto(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [_candidato("R001")]
    verificados = [_verificado("R001")]
    service, mocks = _build_service_with_mocks(
        db=db, candidatos=candidatos, verificados=verificados,
        dictamen_md="# Dictamen David",
    )

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    result = await service.analizar_expediente(
        expediente_con_fase,
        brief_valido,
        user_id="user_123",
        plan="autonomo",
    )

    # Localizar el INSERT a defensia_dictamenes en el log del fake db.
    dictamen_calls = [
        (sql, params)
        for sql, params in db.calls
        if "defensia_dictamenes" in sql and "INSERT" in sql.upper()
    ]
    assert len(dictamen_calls) == 1, (
        f"Se esperaba 1 INSERT a defensia_dictamenes, se hicieron "
        f"{len(dictamen_calls)} — calls={[c[0] for c in db.calls]}"
    )

    sql, params = dictamen_calls[0]

    # Columnas reales segun 20260413_defensia_tables.sql:
    #   id, expediente_id, brief_id, fase_detectada, argumentos_json,
    #   resumen_caso, created_at, modelo_llm, tokens_consumidos
    # NO puede referirse a una columna inventada como `resumen_markdown`.
    assert "resumen_caso" in sql
    assert "resumen_markdown" not in sql
    assert "fase_detectada" in sql
    assert "argumentos_json" in sql

    # Los params deben usar placeholders `?` (parametrizado, no f-string).
    assert sql.count("?") == len(params)

    # El dictamen_id debe empezar por `dict_` (convencion interna).
    assert params[0].startswith("dict_")
    # expediente_id correcto
    assert params[1] == "exp_test_001"

    # El resumen_caso debe contener el markdown del dictamen renderizado.
    assert "# Dictamen David" in params

    # El result expone el id generado.
    assert result["dictamen_id"].startswith("dict_")


# --------------------------------------------------------------------------- #
# Test 10 — SQL INSERT en defensia_escritos con version=1
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_facade_persiste_escrito_con_version_1(
    monkeypatch, expediente_con_fase, brief_valido
):
    db = FakeDB()
    candidatos = [_candidato("R001")]
    verificados = [_verificado("R001")]
    service, mocks = _build_service_with_mocks(
        db=db, candidatos=candidatos, verificados=verificados,
        escrito_md="# Escrito final",
    )

    monkeypatch.setattr(
        "app.services.defensia_rules_engine.evaluar", lambda exp, brief: candidatos
    )
    monkeypatch.setattr("app.services.defensia_rules.load_all", lambda: None)

    result = await service.analizar_expediente(
        expediente_con_fase,
        brief_valido,
        user_id="user_123",
        plan="autonomo",
    )

    escrito_calls = [
        (sql, params)
        for sql, params in db.calls
        if "defensia_escritos" in sql and "INSERT" in sql.upper()
    ]
    assert len(escrito_calls) == 1

    sql, params = escrito_calls[0]

    # Columnas reales: id, expediente_id, dictamen_id, tipo_escrito,
    # contenido_markdown, version, editado_por_usuario, created_at, updated_at.
    assert "contenido_markdown" in sql
    assert "dictamen_id" in sql
    assert "tipo_escrito" in sql
    assert "version" in sql
    assert "editado_por_usuario" in sql
    assert "updated_at" in sql

    assert sql.count("?") == len(params)

    # escrito_id empieza por `esc_`
    assert params[0].startswith("esc_")
    assert params[1] == "exp_test_001"
    # dictamen_id vinculado debe coincidir con el del dictamen persistido
    assert result["dictamen_id"] in params
    # contenido_markdown renderizado
    assert "# Escrito final" in params
    # version=1 presente en los params
    assert 1 in params
    # editado_por_usuario=0 presente
    assert 0 in params
