"""Integration tests — DefensIA Wave 2B endpoints (Batch 3, T2B-013..018).

TestClient con dependency overrides para aislar de Turso/OpenAI/Upstash.
Contract tests del API shape de los ~14 endpoints del router DefensIA.

Los tests estan disenados para ser *contract tests*: verifican el shape
publico del router (status code, headers, claves del body, orden de llamadas
a servicios), no la integracion real con Turso ni OpenAI. Todos los servicios
reales (DefensiaService, DefensiaStorage, DefensiaQuotaService, DefensiaAgent)
se sustituyen por mocks via `app.dependency_overrides`.

Si el router paralelo aun no esta listo cuando se corran estos tests (p. ej.
el modulo `app.services.defensia_dependencies` no existe), *todos* los tests
se marcan como xfail automaticamente con razon explicita. En cuanto el
parallel agent termine, basta con volver a correr pytest: los tests que
cumplan el contrato pasaran a verde sin editar el fichero.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-013..T2B-018
"""
from __future__ import annotations

import importlib
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.jwt_handler import TokenData, get_current_user
from app.models.defensia import TipoDocumento
from app.services.defensia_quota_service import (
    DefensiaQuotaService,
    QuotaExcedida,
)
from app.services.defensia_service import DefensiaService
from app.services.defensia_storage import (
    DefensiaStorage,
    DefensiaStorageUnavailable,
)


# ---------------------------------------------------------------------------
# Deteccion defensiva del router paralelo
# ---------------------------------------------------------------------------
#
# El router Batch 3 (T2B-013..T2B-018) lo esta escribiendo un agent paralelo.
# Mientras no exista el modulo `app.services.defensia_dependencies`, NO podemos
# instalar overrides sobre `Depends(...)` de los endpoints REST nuevos: los
# tests de endpoints fallarian con 404 o ImportError. En ese caso marcamos
# todo (salvo el health stub) como xfail con razon clara.

try:
    defensia_deps = importlib.import_module("app.services.defensia_dependencies")
    DEPS_AVAILABLE = True
except Exception:  # noqa: BLE001 — el modulo puede no existir aun
    defensia_deps = None  # type: ignore[assignment]
    DEPS_AVAILABLE = False


ROUTER_PENDING_REASON = (
    "Router Batch 3 en progreso por agent paralelo — "
    "app.services.defensia_dependencies no disponible aun"
)


def _require_deps() -> None:
    """Marca xfail si el router paralelo aun no ha publicado dependencies."""
    if not DEPS_AVAILABLE:
        pytest.xfail(ROUTER_PENDING_REASON)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_user() -> TokenData:
    """Fake authenticated user — TokenData solo expone user_id/email/exp."""
    return TokenData(user_id="u-test", email="test@defensia.local")


@pytest.fixture
def fake_db() -> MagicMock:
    """Mock TursoClient async. `execute()` devuelve AsyncMock — los tests
    individuales fijan el return value a un MagicMock con `.rows`."""
    db = MagicMock(name="fake_db")
    db.execute = AsyncMock()
    # Default: result sin filas (tipico de operaciones de escritura).
    db.execute.return_value = MagicMock(rows=[])
    return db


@pytest.fixture
def fake_storage() -> MagicMock:
    """DefensiaStorage habilitado con cifrar() mockeado."""
    storage = MagicMock(spec=DefensiaStorage)
    storage.is_enabled = True
    storage.cifrar.return_value = (b"fake_cipher", b"fake_nonce_123")
    storage.descifrar.return_value = b"plain"
    return storage


@pytest.fixture
def fake_quota() -> AsyncMock:
    """DefensiaQuotaService con `puede_consumir=True` y estado vacio."""
    quota = AsyncMock(spec=DefensiaQuotaService)
    quota.puede_consumir.return_value = True
    quota._get_estado.return_value = {"expedientes_creados": 0, "en_curso": 0}
    quota.reserve.return_value = "res_fake"
    quota.commit.return_value = None
    quota.release.return_value = None
    return quota


@pytest.fixture
def fake_service() -> AsyncMock:
    """DefensiaService facade con analizar_expediente mockeado."""
    service = AsyncMock(spec=DefensiaService)
    service.analizar_expediente.return_value = {
        "escrito_markdown": "# Escrito\n\nCuerpo del escrito.",
        "dictamen_markdown": "# Dictamen\n\nResumen.",
        "argumentos_verificados": [],
        "argumentos_descartados_count": 0,
        "reserva_id": "res_fake",
        "dictamen_id": "dict_fake",
        "escrito_id": "esc_fake",
        "expediente_id": "exp_fake",
        "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
    }
    return service


@pytest.fixture
def fake_writer() -> MagicMock:
    """DefensiaWriter mock — solo hace falta para endpoints que lo pidan."""
    writer = MagicMock(name="fake_writer")
    writer.render_escrito.return_value = "# Escrito mockeado"
    writer.render_dictamen.return_value = "# Dictamen mockeado"
    return writer


@pytest.fixture
def fake_export() -> MagicMock:
    """DefensiaExportService mock — devuelve bytes fake para docx/pdf."""
    export = MagicMock(name="fake_export")
    export.markdown_a_docx.return_value = b"FAKE_DOCX_BYTES"
    export.markdown_a_pdf.return_value = b"%PDF-FAKE"
    return export


@pytest.fixture
def fake_rag_verifier() -> AsyncMock:
    """RAG verifier mock — devuelve lista vacia de argumentos verificados."""
    rag = AsyncMock(name="fake_rag")
    rag.verify_all.return_value = []
    return rag


@pytest.fixture
def fake_agent():
    """DefensiaAgent con chat_stream async que yields 3 chunks fijos."""

    async def _fake_stream(message, chat_history=None):
        yield "Hola "
        yield "desde "
        yield "DefensIA."

    agent = MagicMock(name="fake_agent")
    agent.chat_stream = _fake_stream
    return agent


@pytest.fixture(autouse=True)
def _reset_sse_starlette_event():
    """Workaround sse_starlette + TestClient: el `AppStatus.should_exit_event`
    es un `asyncio.Event` cacheado a nivel de modulo. Cada test crea un
    nuevo event loop, y si el evento quedo atado a un loop anterior
    `sse_starlette` crashea con ``RuntimeError: bound to a different event loop``.
    Resetearlo antes de cada test restaura el comportamiento estable.
    """
    try:
        from sse_starlette.sse import AppStatus

        AppStatus.should_exit_event = None
    except Exception:  # noqa: BLE001 — defensive, la lib puede cambiar
        pass
    yield
    try:
        from sse_starlette.sse import AppStatus

        AppStatus.should_exit_event = None
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture
def client(
    fake_user: TokenData,
    fake_db: MagicMock,
    fake_storage: MagicMock,
    fake_quota: AsyncMock,
    fake_service: AsyncMock,
    fake_writer: MagicMock,
    fake_export: MagicMock,
    fake_rag_verifier: AsyncMock,
    fake_agent: MagicMock,
) -> Iterator[TestClient]:
    """TestClient con dependency overrides para aislar servicios externos.

    Si `defensia_dependencies` aun no existe (router paralelo en progreso),
    solo se instalan los overrides que si podemos resolver (get_current_user).
    """
    # get_current_user siempre existe — el stub Parte 1 ya lo importa.
    app.dependency_overrides[get_current_user] = lambda: fake_user

    # Overrides de dependencies DefensIA — solo si el modulo existe.
    if DEPS_AVAILABLE:
        # Los nombres siguen la convencion get_<servicio> del plan T2B-013..018.
        # Si alguno no existe en el modulo aun, el getattr devuelve None y
        # nos saltamos ese override sin romper el resto.
        overrides_map = {
            "get_db": lambda: fake_db,
            "get_defensia_storage": lambda: fake_storage,
            "get_defensia_quota_service": lambda: fake_quota,
            "get_defensia_service": lambda: fake_service,
            "get_defensia_writer": lambda: fake_writer,
            "get_defensia_export": lambda: fake_export,
            "get_defensia_rag_verifier": lambda: fake_rag_verifier,
            "get_defensia_agent": lambda: fake_agent,
        }
        for name, factory in overrides_map.items():
            dep = getattr(defensia_deps, name, None)
            if dep is not None:
                app.dependency_overrides[dep] = factory

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client() -> Iterator[TestClient]:
    """TestClient SIN overrides de auth — para tests 401."""
    # Limpia cualquier override residual y no instala get_current_user.
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers — rows de fake DB
# ---------------------------------------------------------------------------


def _row_result(rows: list[dict[str, Any]]) -> MagicMock:
    """Crea un MagicMock con `.rows=[...]` para fake_db.execute.return_value."""
    result = MagicMock()
    result.rows = rows
    return result


def _side_effect_rows(*row_batches: list[dict[str, Any]]):
    """Genera un side_effect que devuelve batches en orden por cada execute()."""
    batches = [MagicMock(rows=b) for b in row_batches]

    async def _effect(*args, **kwargs):
        if batches:
            return batches.pop(0)
        return MagicMock(rows=[])

    return _effect


# ===========================================================================
# 1. Health — publico, sin auth
# ===========================================================================


def test_health_no_auth():
    """GET /api/defensia/_health — responde 200 sin token, cualquier shape
    razonable ({status: ok} con o sin `module`) cuenta como PASS.
    """
    # No instalamos overrides ni auth — el endpoint es publico.
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        response = c.get("/api/defensia/_health")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("status") == "ok"


# ===========================================================================
# 2. Expediente CRUD (T2B-013 + T2B-017)
# ===========================================================================


def test_crear_expediente_201(client: TestClient, fake_db: MagicMock):
    _require_deps()
    payload = {
        "nombre": "Reclamacion IRPF 2024",
        "tributo": "IRPF",
        "ccaa": "Madrid",
        "tipo_procedimiento_declarado": "LIQUIDACION",
    }
    response = client.post("/api/defensia/expedientes", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    assert data.get("nombre") == payload["nombre"]
    assert data.get("tributo") == "IRPF"
    # estado por defecto segun schema SQL: 'borrador'
    assert data.get("estado", "borrador") == "borrador"
    # Se inserto al menos una fila
    assert fake_db.execute.await_count >= 1


def test_listar_expedientes_devuelve_items(
    client: TestClient, fake_db: MagicMock
):
    _require_deps()
    fake_db.execute.return_value = _row_result(
        [
            {
                "id": "e1",
                "user_id": "u-test",
                "nombre": "Exp 1",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "estado": "borrador",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            },
            {
                "id": "e2",
                "user_id": "u-test",
                "nombre": "Exp 2",
                "tributo": "IVA",
                "ccaa": "Cataluna",
                "estado": "dictamen_listo",
                "tipo_procedimiento_declarado": "COMPROBACION",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-13T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            },
        ]
    )
    response = client.get("/api/defensia/expedientes")
    assert response.status_code == 200, response.text
    data = response.json()
    items = data.get("items", data if isinstance(data, list) else [])
    assert len(items) == 2
    assert {i["id"] for i in items} == {"e1", "e2"}


def test_detalle_expediente_ok(client: TestClient, fake_db: MagicMock):
    _require_deps()
    # El endpoint puede hacer 3-5 SELECTs (exp, docs, briefs, dictamenes,
    # escritos). Devolvemos el expediente en la primera llamada y listas
    # vacias en las siguientes.
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "Mi exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "fase_confianza": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],  # documentos
        [],  # briefs
        [],  # dictamenes
        [],  # escritos
    )
    response = client.get("/api/defensia/expedientes/exp-1")
    assert response.status_code == 200, response.text
    data = response.json()
    assert ("expediente" in data) or ("id" in data)


def test_detalle_expediente_not_found(
    client: TestClient, fake_db: MagicMock
):
    _require_deps()
    fake_db.execute.return_value = _row_result([])  # no existe
    response = client.get("/api/defensia/expedientes/no-existe")
    assert response.status_code == 404


# ===========================================================================
# 3. Ownership checks (H3 — not found > forbidden)
# ===========================================================================


def test_ownership_check_404_si_otro_user(
    client: TestClient, fake_db: MagicMock
):
    """H3: si el expediente pertenece a otro user_id debemos devolver 404,
    NO 403, para no filtrar existencia."""
    _require_deps()
    # El WHERE del router deberia incluir user_id = ? asi que devolvemos
    # lista vacia: el router debe traducirlo a 404.
    fake_db.execute.return_value = _row_result([])
    response = client.get("/api/defensia/expedientes/exp-otro")
    assert response.status_code == 404
    # Nunca 403 (no revelar existencia)
    assert response.status_code != 403


def test_delete_expediente_cascade(
    client: TestClient, fake_db: MagicMock
):
    _require_deps()
    # Primero devolvemos el expediente (existe y es del user), luego el
    # DELETE no devuelve filas.
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],
    )
    response = client.delete("/api/defensia/expedientes/exp-1")
    assert response.status_code in (200, 204)
    # Verifica que el DELETE se ejecuto
    assert fake_db.execute.await_count >= 1


# ===========================================================================
# 4. Documentos (T2B-013) — Regla #1 invariante H4
# ===========================================================================


def test_upload_documento_storage_enabled_201(
    client: TestClient,
    fake_db: MagicMock,
    fake_storage: MagicMock,
):
    """POST /documentos con storage habilitado inserta en defensia_documentos
    pero NO crea dictamen ni escrito (invariante H4 del plan-checker —
    Regla #1 del producto DefensIA)."""
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {  # SELECT expediente para check de ownership
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],  # INSERT defensia_documentos
    )
    files = {"file": ("liquidacion.pdf", b"%PDF-1.4 fake", "application/pdf")}
    response = client.post(
        "/api/defensia/expedientes/exp-1/documentos", files=files
    )
    assert response.status_code == 201, response.text
    # storage.cifrar fue llamado
    fake_storage.cifrar.assert_called()


def test_upload_documento_storage_disabled_503(
    client: TestClient,
    fake_db: MagicMock,
    fake_storage: MagicMock,
):
    _require_deps()
    fake_storage.is_enabled = False
    fake_storage.cifrar.side_effect = DefensiaStorageUnavailable(
        "storage key not set"
    )
    fake_db.execute.return_value = _row_result(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ]
    )
    files = {"file": ("x.pdf", b"%PDF", "application/pdf")}
    response = client.post(
        "/api/defensia/expedientes/exp-1/documentos", files=files
    )
    assert response.status_code == 503


def test_upload_dispara_fase1_auto_extraccion(
    client: TestClient,
    fake_db: MagicMock,
    fake_storage: MagicMock,
    monkeypatch,
):
    """Regresion: tras subir un documento, el endpoint debe ejecutar Fase 1
    (classifier + extractor + phase detector) y devolver en la response los
    campos auto-detectados (tipo_documento, clasificacion_confianza,
    fase_detectada). Antes del wire-up, el endpoint solo persistia bytes
    cifrados y el wizard llegaba al paso 3 con fase=None.

    Mockeamos classifier, extractor y phase_detector para no golpear Gemini.
    """
    _require_deps()

    # ---- Mock classifier ----
    from app.services import defensia_document_classifier as _dc

    class _FakeClassification:
        tipo = TipoDocumento.LIQUIDACION_PROVISIONAL
        confianza = 0.92
        fuente = "regex"

    class _FakeClassifier:
        def classify_text(self, texto: str):
            return _FakeClassification()

    monkeypatch.setattr(_dc, "DocumentClassifier", _FakeClassifier)

    # ---- Mock extractor ----
    from app.services import defensia_data_extractor as _ext

    def _fake_extract_liquidacion(pdf_bytes, nombre):
        return {
            "referencia": "1234567890",
            "fecha_acto": "2026-01-15",
            "importe_total": 3200.50,
            "gastos_adquisicion_declarados": 15000.0,
            "gastos_adquisicion_admitidos": 8000.0,
            "diff_gastos_adquisicion_no_admitidos": 7000.0,
        }

    monkeypatch.setattr(
        _ext,
        "extract_liquidacion_provisional",
        _fake_extract_liquidacion,
    )

    # ---- Mock PDF text extractor (for classifier input) ----
    async def _fake_extract_pdf(pdf_bytes, nombre):
        class _R:
            full_text = "Liquidacion provisional IRPF fake text"
            success = True
        return _R()

    import app.utils.pdf_extractor as _pdf_mod

    monkeypatch.setattr(
        _pdf_mod,
        "extract_pdf_text_plain",
        _fake_extract_pdf,
    )

    # ---- Mock phase detector ----
    from app.services import defensia_phase_detector as _pd
    from app.models.defensia import Fase

    def _fake_detect_fase(expediente, hoy=None):
        return Fase.LIQUIDACION_FIRME_PLAZO_RECURSO, 0.9

    monkeypatch.setattr(_pd, "detect_fase", _fake_detect_fase)

    # ---- Fake DB con ownership + post-insert selects ----
    ownership_row = {
        "id": "exp-1",
        "user_id": "u-test",
        "nombre": "exp",
        "tributo": "IRPF",
        "ccaa": "Madrid",
        "tipo_procedimiento_declarado": "LIQUIDACION",
        "estado": "borrador",
        "fase_detectada": None,
        "fase_confianza": None,
        "created_at": "2026-04-14T00:00:00Z",
        "updated_at": "2026-04-14T00:00:00Z",
    }
    doc_row_after_update = {
        "id": "doc-1",
        "nombre_original": "liquidacion.pdf",
        "tipo_documento": "LIQUIDACION_PROVISIONAL",
        "fecha_acto": "2026-01-15",
        "datos_estructurados_json": '{"referencia":"1234567890"}',
    }
    exp_for_recompute = {"tributo": "IRPF", "ccaa": "Madrid"}

    batches = [
        [ownership_row],  # SELECT ownership
        [],  # INSERT defensia_documentos
        [],  # UPDATE defensia_expedientes (touch updated_at)
        [],  # UPDATE defensia_documentos fase1 metadata
        [exp_for_recompute],  # SELECT expediente (recompute fase)
        [doc_row_after_update],  # SELECT documentos (recompute fase)
        [],  # UPDATE defensia_expedientes fase_detectada
    ]
    fake_db.execute.side_effect = _side_effect_rows(*batches)

    files = {
        "file": (
            "liquidacion.pdf",
            b"%PDF-1.4 fake content",
            "application/pdf",
        )
    }
    response = client.post(
        "/api/defensia/expedientes/exp-1/documentos", files=files
    )
    assert response.status_code == 201, response.text

    body = response.json()
    # La respuesta debe incluir los campos auto-detectados
    assert body["tipo_documento"] == "LIQUIDACION_PROVISIONAL"
    assert body["clasificacion_confianza"] == pytest.approx(0.92)
    assert body["fecha_acto"] == "2026-01-15"
    assert body["fase_detectada"] == "LIQUIDACION_FIRME_PLAZO_RECURSO"
    assert body["fase_confianza"] == pytest.approx(0.9)

    # Se hizo al menos un UPDATE a defensia_documentos con tipo_documento
    all_sql = " ".join(
        str(call.args[0]) if call.args else ""
        for call in fake_db.execute.await_args_list
    ).lower()
    assert "update defensia_documentos" in all_sql
    assert "tipo_documento" in all_sql
    # Y un UPDATE a defensia_expedientes con fase_detectada
    assert "fase_detectada" in all_sql


def test_upload_fase1_resiliente_si_gemini_falla(
    client: TestClient,
    fake_db: MagicMock,
    fake_storage: MagicMock,
    monkeypatch,
):
    """Regresion: si el classifier o extractor lanzan (Gemini down), el
    upload DEBE seguir devolviendo 201 — best-effort. El usuario ve el
    documento subido sin campos auto-detectados pero la feature sigue
    funcional."""
    _require_deps()

    # Classifier explota
    from app.services import defensia_document_classifier as _dc

    class _BoomClassifier:
        def classify_text(self, texto):
            raise RuntimeError("Gemini rate limit")

    monkeypatch.setattr(_dc, "DocumentClassifier", _BoomClassifier)

    async def _fake_extract_pdf(pdf_bytes, nombre):
        class _R:
            full_text = "Algun texto"
            success = True
        return _R()

    import app.utils.pdf_extractor as _pdf_mod
    monkeypatch.setattr(_pdf_mod, "extract_pdf_text_plain", _fake_extract_pdf)

    fake_db.execute.side_effect = _side_effect_rows(
        [{
            "id": "exp-1",
            "user_id": "u-test",
            "nombre": "exp",
            "tributo": "IRPF",
            "ccaa": "Madrid",
            "tipo_procedimiento_declarado": "LIQUIDACION",
            "estado": "borrador",
            "fase_detectada": None,
            "created_at": "2026-04-14T00:00:00Z",
            "updated_at": "2026-04-14T00:00:00Z",
        }],
        [], [], [],  # INSERT + 2 UPDATEs
        [{"tributo": "IRPF", "ccaa": "Madrid"}],  # SELECT recompute
        [],  # SELECT docs (empty, ningun doc clasificado)
        [],  # UPDATE fase
    )

    files = {"file": ("x.pdf", b"%PDF", "application/pdf")}
    response = client.post(
        "/api/defensia/expedientes/exp-1/documentos", files=files
    )
    assert response.status_code == 201
    body = response.json()
    # Sin classifier funcional, tipo queda None/null
    assert body["tipo_documento"] is None


def test_upload_documento_no_crea_dictamen_ni_escrito(
    client: TestClient,
    fake_db: MagicMock,
    fake_service: AsyncMock,
):
    """H4: POST /documentos NO debe disparar analizar_expediente (Regla #1:
    el analisis solo arranca con brief explicito + POST /analyze)."""
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],
    )
    files = {"file": ("x.pdf", b"%PDF", "application/pdf")}
    client.post("/api/defensia/expedientes/exp-1/documentos", files=files)

    # Invariante H4: el facade NO debe ser invocado por /documentos.
    assert fake_service.analizar_expediente.await_count == 0

    # Ninguna query debe mencionar defensia_dictamenes o defensia_escritos.
    all_sql = " ".join(
        str(call.args[0]) if call.args else ""
        for call in fake_db.execute.await_args_list
    ).lower()
    assert "defensia_dictamenes" not in all_sql
    assert "defensia_escritos" not in all_sql


# ===========================================================================
# 5. Brief (T2B-018)
# ===========================================================================


def test_crear_brief_201(client: TestClient, fake_db: MagicMock):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],
    )
    response = client.post(
        "/api/defensia/expedientes/exp-1/brief",
        json={"texto": "La Administracion me reclama IRPF 2024 sin motivo."},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    assert data.get("texto") or "texto" in data


def test_get_brief_devuelve_ultimo(
    client: TestClient, fake_db: MagicMock
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "brief-1",
                "expediente_id": "exp-1",
                "texto": "Texto brief",
                "chat_history_json": None,
                "created_at": "2026-04-14T00:00:00Z",
            }
        ],
    )
    response = client.get("/api/defensia/expedientes/exp-1/brief")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("texto") == "Texto brief" or "texto" in data


def test_put_brief_actualiza(client: TestClient, fake_db: MagicMock):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": None,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "brief-1",
                "expediente_id": "exp-1",
                "texto": "antiguo",
                "chat_history_json": None,
                "created_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],  # UPDATE
    )
    response = client.put(
        "/api/defensia/expedientes/exp-1/brief",
        json={"texto": "Brief actualizado"},
    )
    assert response.status_code == 200, response.text


# ===========================================================================
# 6. Analyze SSE (T2B-014)
# ===========================================================================


def test_analyze_sse_happy_path(
    client: TestClient,
    fake_db: MagicMock,
    fake_service: AsyncMock,
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "brief-1",
                "expediente_id": "exp-1",
                "texto": "brief",
                "chat_history_json": None,
                "created_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],
    )
    with client.stream(
        "POST",
        "/api/defensia/expedientes/exp-1/analyze",
    ) as response:
        assert response.status_code == 200, response.read()
        ct = response.headers.get("content-type", "")
        assert "text/event-stream" in ct, ct
        body = b"".join(response.iter_bytes()).decode("utf-8", errors="replace")
    # Al menos un evento SSE
    assert "event:" in body or "data:" in body
    # El facade fue invocado exactamente una vez
    assert fake_service.analizar_expediente.await_count == 1


def test_analyze_sse_quota_excedida_402(
    client: TestClient,
    fake_db: MagicMock,
    fake_service: AsyncMock,
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "brief-1",
                "expediente_id": "exp-1",
                "texto": "brief",
                "chat_history_json": None,
                "created_at": "2026-04-14T00:00:00Z",
            }
        ],
    )
    fake_service.analizar_expediente.side_effect = QuotaExcedida(
        "Cuota mensual agotada"
    )
    with client.stream(
        "POST",
        "/api/defensia/expedientes/exp-1/analyze",
    ) as response:
        status = response.status_code
        body = b"".join(response.iter_bytes()).decode("utf-8", errors="replace")
    # Dos patterns validos:
    #   (a) el router traduce QuotaExcedida a HTTP 402 antes de abrir el stream
    #   (b) el router captura la excepcion dentro del stream y emite un evento
    #       SSE con code=quota_excedida + http_status=402
    assert (
        status == 402
        or "402" in body
        or "quota_excedida" in body.lower()
        or "quota" in body.lower()
    )


def test_analyze_sse_rechaza_si_no_brief(
    client: TestClient, fake_db: MagicMock
):
    """Regla #1: el analisis requiere brief. Si no hay brief, el endpoint
    debe rechazar. Si la implementacion no chequea esto explicitamente
    (lo delega al service via Brief obligatorio en el modelo), el test
    igualmente puede comprobar que el endpoint no devuelve 200 con dictamen.
    """
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "borrador",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],  # no briefs
    )
    with client.stream(
        "POST",
        "/api/defensia/expedientes/exp-1/analyze",
    ) as response:
        status = response.status_code
        body = b"".join(response.iter_bytes()).decode("utf-8", errors="replace")
    # Debe fallar: 400/409/422, o bien 200 con evento SSE de error.
    assert status >= 400 or "error" in body.lower() or "brief" in body.lower()


# ===========================================================================
# 7. Dictamen + Export (T2B-015)
# ===========================================================================


def test_get_dictamen_ok(client: TestClient, fake_db: MagicMock):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "dictamen_listo",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "dict_1",
                "expediente_id": "exp-1",
                "brief_id": None,
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "argumentos_json": "[]",
                "resumen_caso": "# Dictamen",
                "created_at": "2026-04-14T00:00:00Z",
                "modelo_llm": "gpt-5-mini",
                "tokens_consumidos": None,
            }
        ],
    )
    response = client.get("/api/defensia/expedientes/exp-1/dictamen")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "dictamen" in data or "argumentos" in data or "id" in data


def test_export_docx_devuelve_bytes(
    client: TestClient,
    fake_db: MagicMock,
    fake_export: MagicMock,
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "dictamen_listo",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "esc_1",
                "expediente_id": "exp-1",
                "dictamen_id": "dict_1",
                "tipo_escrito": "RECURSO_REPOSICION",
                "contenido_markdown": "# Escrito\nCuerpo",
                "version": 1,
                "editado_por_usuario": 0,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
    )
    response = client.get(
        "/api/defensia/expedientes/exp-1/escrito/esc_1/export",
        params={"format": "docx"},
    )
    assert response.status_code == 200, response.text
    ct = response.headers.get("content-type", "")
    assert "wordprocessingml" in ct or "octet-stream" in ct or "docx" in ct
    assert len(response.content) > 0


def test_export_pdf_devuelve_bytes(
    client: TestClient,
    fake_db: MagicMock,
    fake_export: MagicMock,
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "dictamen_listo",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "esc_1",
                "expediente_id": "exp-1",
                "dictamen_id": "dict_1",
                "tipo_escrito": "RECURSO_REPOSICION",
                "contenido_markdown": "# Escrito",
                "version": 1,
                "editado_por_usuario": 0,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
    )
    response = client.get(
        "/api/defensia/expedientes/exp-1/escrito/esc_1/export",
        params={"format": "pdf"},
    )
    assert response.status_code == 200, response.text
    ct = response.headers.get("content-type", "")
    assert "pdf" in ct or "octet-stream" in ct
    assert len(response.content) > 0


# ===========================================================================
# 8. PATCH escrito (T2B-015b)
# ===========================================================================


def test_patch_escrito_incrementa_version(
    client: TestClient, fake_db: MagicMock
):
    _require_deps()
    fake_db.execute.side_effect = _side_effect_rows(
        [
            {
                "id": "exp-1",
                "user_id": "u-test",
                "nombre": "exp",
                "tributo": "IRPF",
                "ccaa": "Madrid",
                "tipo_procedimiento_declarado": "LIQUIDACION",
                "estado": "dictamen_listo",
                "fase_detectada": "LIQUIDACION_FIRME_PLAZO_RECURSO",
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [
            {
                "id": "esc_1",
                "expediente_id": "exp-1",
                "dictamen_id": "dict_1",
                "tipo_escrito": "RECURSO_REPOSICION",
                "contenido_markdown": "# Antes",
                "version": 1,
                "editado_por_usuario": 0,
                "created_at": "2026-04-14T00:00:00Z",
                "updated_at": "2026-04-14T00:00:00Z",
            }
        ],
        [],  # UPDATE
    )
    response = client.patch(
        "/api/defensia/expedientes/exp-1/escrito/esc_1",
        json={"contenido_markdown": "# Despues"},
    )
    assert response.status_code == 200, response.text
    # El SQL de UPDATE debe tocar `version` (incrementar) y
    # `editado_por_usuario`.
    all_sql = " ".join(
        str(call.args[0]) if call.args else ""
        for call in fake_db.execute.await_args_list
    ).lower()
    assert "update" in all_sql and "version" in all_sql


# ===========================================================================
# 9. Chat SSE (T2B-016)
# ===========================================================================


def test_chat_sse_happy_path(client: TestClient):
    _require_deps()
    with client.stream(
        "POST",
        "/api/defensia/chat",
        json={"message": "Hola, necesito ayuda con una liquidacion IRPF."},
    ) as response:
        assert response.status_code == 200, response.read()
        ct = response.headers.get("content-type", "")
        assert "text/event-stream" in ct
        body = b"".join(response.iter_bytes()).decode("utf-8", errors="replace")
    # El fake_agent yields "Hola ", "desde ", "DefensIA."
    assert "DefensIA" in body or "Hola" in body


def test_chat_sse_no_auth_401(unauth_client: TestClient):
    """Sin override de get_current_user → 401."""
    _require_deps()
    response = unauth_client.post(
        "/api/defensia/chat",
        json={"message": "Hola"},
    )
    assert response.status_code in (401, 403)


# ===========================================================================
# 10. Cuotas (T2B-017)
# ===========================================================================


def test_get_cuotas_devuelve_estado(
    client: TestClient,
    fake_db: MagicMock,
    fake_quota: AsyncMock,
):
    _require_deps()
    # El endpoint puede consultar el subscription_plan del user_id antes de
    # calcular cuotas. Devolvemos una row con plan = 'particular'.
    fake_db.execute.return_value = _row_result(
        [{"subscription_plan": "particular", "id": "u-test"}]
    )
    fake_quota._get_estado.return_value = {
        "expedientes_creados": 0,
        "en_curso": 0,
    }
    response = client.get("/api/defensia/cuotas")
    assert response.status_code == 200, response.text
    data = response.json()
    # El shape exacto puede variar pero debe tener limite + creados + plan.
    assert "plan" in data or "limite" in data or "disponibles" in data
