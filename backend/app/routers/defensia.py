"""DefensIA REST router — Wave 2B Batch 3.

Expone los endpoints REST de DefensIA sobre los servicios orquestados en
``app/services/defensia_*.py``. Todos los endpoints (excepto ``_health``)
requieren autenticacion JWT y verifican ownership del expediente antes de
operar.

Reglas de disenho (cerradas en el plan v2)
-----------------------------------------
1. **Regla #1 del producto**: la Fase 1 (extraccion tecnica) puede dispararse
   al subir documentos, pero las fases 2-4 (reglas + verificador + escrito)
   solo se ejecutan cuando el usuario hace ``POST /expedientes/{id}/analyze``
   explicitamente con un brief ya guardado.
2. **Ownership check** en todos los endpoints que tocan un expediente. Si la
   fila no existe o pertenece a otro usuario, devolvemos 404 (nunca 403) para
   no revelar la existencia del recurso.
3. **SQL parametrizado siempre** (``?`` placeholders). Nunca f-strings con
   datos de usuario.
4. **SSE** (``analyze`` y ``chat``) via ``EventSourceResponse`` de
   ``sse_starlette`` — identico patron al router ``chat_stream.py``.
5. **Rate limits** via ``@limiter.limit(...)`` de ``slowapi`` con los valores
   del modulo ``defensia_rate_limits``. El primer parametro del endpoint DEBE
   llamarse ``request: Request`` (requisito de slowapi).
6. **Tildes** en strings visibles al usuario.
7. **UTC** siempre (``datetime.now(timezone.utc)``), nunca ``utcnow``.
"""

import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.auth.jwt_handler import TokenData, get_current_user
from app.database.turso_client import TursoClient
from app.models.defensia import (
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.security.defensia_rate_limits import get_defensia_rate_limit
from app.security.rate_limiter import limiter
from app.services.defensia_dependencies import (
    get_db,
    get_defensia_agent,
    get_defensia_export,
    get_defensia_quota_service,
    get_defensia_service,
    get_defensia_storage,
)
from app.services.defensia_export_service import DefensiaExportService
from app.services.defensia_quota_service import (
    LIMITES_POR_PLAN,
    PRECIO_EXTRA_POR_PLAN,
    DefensiaQuotaService,
    QuotaExcedida,
)
from app.services.defensia_service import DefensiaService
from app.services.defensia_storage import DefensiaStorage, DefensiaStorageUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/defensia", tags=["defensia"])


# ============================================================================
# Pydantic request/response bodies
# ============================================================================


class CrearExpedienteRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    tributo: Tributo
    ccaa: str = Field(..., min_length=1, max_length=100)
    tipo_procedimiento_declarado: str = Field(..., min_length=1, max_length=100)


class BriefRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=10_000)


class EditarEscritoRequest(BaseModel):
    contenido_markdown: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    chat_history: Optional[list[dict[str, str]]] = None


# ============================================================================
# Helpers
# ============================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _ensure_owner(
    db: TursoClient, exp_id: str, user_id: str
) -> dict[str, Any]:
    """Verifica ownership del expediente y devuelve la fila.

    Devuelve 404 tanto si no existe como si pertenece a otro usuario (no
    revelamos la distincion por seguridad).
    """
    result = await db.execute(
        "SELECT id, user_id, nombre, tributo, ccaa, tipo_procedimiento_declarado, "
        "fase_detectada, fase_confianza, estado, created_at, updated_at "
        "FROM defensia_expedientes WHERE id = ? AND user_id = ?",
        [exp_id, user_id],
    )
    if not result or not getattr(result, "rows", None):
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return dict(result.rows[0])


def _map_fase(value: Optional[str]) -> Fase:
    """Normaliza un string de fase a ``Fase`` — si es None/invalido, INDETERMINADA."""
    if not value:
        return Fase.INDETERMINADA
    try:
        return Fase(value)
    except ValueError:
        return Fase.INDETERMINADA


def _row_a_expediente(exp_row: dict[str, Any]) -> ExpedienteEstructurado:
    """Construye un ``ExpedienteEstructurado`` minimal desde una fila SQL.

    No carga documentos — el endpoint ``/analyze`` confia en que los
    documentos se han procesado en paso previo (upload + extraccion). Si en
    el futuro el facade necesita releer documentos, anadir aqui una query
    separada y documentarlo.
    """
    try:
        tributo = Tributo(exp_row.get("tributo") or "IRPF")
    except ValueError:
        tributo = Tributo.IRPF
    return ExpedienteEstructurado(
        id=exp_row["id"],
        tributo=tributo,
        ccaa=exp_row.get("ccaa") or "",
        documentos=[],
        fase_detectada=_map_fase(exp_row.get("fase_detectada")),
        fase_confianza=float(exp_row.get("fase_confianza") or 0.0),
    )


async def _load_last_brief(db: TursoClient, exp_id: str) -> Optional[Brief]:
    """Devuelve el brief mas reciente del expediente (o None si no hay)."""
    result = await db.execute(
        "SELECT id, texto, chat_history_json FROM defensia_briefs "
        "WHERE expediente_id = ? ORDER BY created_at DESC LIMIT 1",
        [exp_id],
    )
    if not result or not getattr(result, "rows", None):
        return None
    row = result.rows[0]
    chat_history: list[dict[str, str]] = []
    raw_chat = row.get("chat_history_json")
    if raw_chat:
        try:
            parsed = json.loads(raw_chat) if isinstance(raw_chat, str) else raw_chat
            if isinstance(parsed, list):
                chat_history = parsed
        except (json.JSONDecodeError, TypeError):
            chat_history = []
    return Brief(id=row["id"], texto=row.get("texto") or "", chat_history=chat_history)


async def _resolver_plan_usuario(db: TursoClient, user_id: str) -> str:
    """Devuelve el plan del usuario para el QuotaService DefensIA.

    Lee de forma tolerante las tablas ``users`` y ``subscriptions`` usando el
    ``TursoClient`` inyectado (no crea su propia conexion, asi los tests con
    overrides de ``get_db`` funcionan sin tocar el subscription_service).

    Reglas:
        - ``is_owner = 1`` -> ``creator`` (limite mas alto).
        - ``subscriptions.plan_type`` en LIMITES_POR_PLAN -> se usa tal cual.
        - Cualquier otro caso -> ``particular`` (plan mas restrictivo, no
          bloqueamos al usuario pero aplicamos la cuota minima).
    """
    try:
        result = await db.execute(
            "SELECT u.is_owner, s.plan_type "
            "FROM users u LEFT JOIN subscriptions s ON s.user_id = u.id "
            "WHERE u.id = ?",
            [user_id],
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, nunca bloquea
        logger.warning(
            "DefensIA: error leyendo plan de usuario %s: %s", user_id, exc
        )
        return "particular"

    if not result or not getattr(result, "rows", None):
        return "particular"
    row = result.rows[0]
    if row.get("is_owner"):
        return "creator"
    plan = (row.get("plan_type") or "").lower()
    if plan in LIMITES_POR_PLAN:
        return plan
    return "particular"


# ============================================================================
# Endpoint 1 — Health
# ============================================================================


@router.get("/_health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "defensia"}


# ============================================================================
# Endpoint 2 — Crear expediente
# ============================================================================


@router.post("/expedientes", status_code=status.HTTP_201_CREATED)
@limiter.limit(get_defensia_rate_limit("default"))
async def crear_expediente(
    request: Request,
    body: CrearExpedienteRequest,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Crea un expediente en estado ``borrador``.

    No consume cuota — solo el pipeline ``analyze`` llama a
    ``quota_service.reserve``.
    """
    exp_id = f"exp_{secrets.token_urlsafe(12)}"
    now = _now_iso()

    await db.execute(
        "INSERT INTO defensia_expedientes "
        "(id, user_id, nombre, tributo, ccaa, tipo_procedimiento_declarado, "
        "estado, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'borrador', ?, ?)",
        [
            exp_id,
            current_user.user_id,
            body.nombre,
            body.tributo.value,
            body.ccaa,
            body.tipo_procedimiento_declarado,
            now,
            now,
        ],
    )
    logger.info(
        "DefensIA: expediente creado id=%s user=%s tributo=%s",
        exp_id,
        current_user.user_id,
        body.tributo.value,
    )
    return {
        "id": exp_id,
        "nombre": body.nombre,
        "tributo": body.tributo.value,
        "ccaa": body.ccaa,
        "tipo_procedimiento_declarado": body.tipo_procedimiento_declarado,
        "estado": "borrador",
        "created_at": now,
    }


# ============================================================================
# Endpoint 3 — Listar expedientes
# ============================================================================


@router.get("/expedientes")
@limiter.limit(get_defensia_rate_limit("default"))
async def listar_expedientes(
    request: Request,
    estado: Optional[str] = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Lista los expedientes del usuario, opcionalmente filtrando por estado."""
    if estado:
        result = await db.execute(
            "SELECT id, nombre, tributo, ccaa, fase_detectada, estado, updated_at "
            "FROM defensia_expedientes "
            "WHERE user_id = ? AND estado = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            [current_user.user_id, estado, limit],
        )
    else:
        result = await db.execute(
            "SELECT id, nombre, tributo, ccaa, fase_detectada, estado, updated_at "
            "FROM defensia_expedientes "
            "WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            [current_user.user_id, limit],
        )
    items = [dict(r) for r in (result.rows or [])] if result else []
    return {"items": items}


# ============================================================================
# Endpoint 4 — Detalle expediente (con timeline)
# ============================================================================


@router.get("/expedientes/{exp_id}")
@limiter.limit(get_defensia_rate_limit("default"))
async def detalle_expediente(
    request: Request,
    exp_id: str,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Devuelve el expediente + documentos + briefs + dictamenes + escritos."""
    expediente = await _ensure_owner(db, exp_id, current_user.user_id)

    docs_res = await db.execute(
        "SELECT id, nombre_original, tipo_documento, fecha_acto, "
        "clasificacion_confianza, created_at "
        "FROM defensia_documentos WHERE expediente_id = ? ORDER BY fecha_acto ASC",
        [exp_id],
    )
    briefs_res = await db.execute(
        "SELECT id, texto, created_at FROM defensia_briefs "
        "WHERE expediente_id = ? ORDER BY created_at DESC",
        [exp_id],
    )
    dicts_res = await db.execute(
        "SELECT id, fase_detectada, created_at FROM defensia_dictamenes "
        "WHERE expediente_id = ? ORDER BY created_at DESC",
        [exp_id],
    )
    escritos_res = await db.execute(
        "SELECT id, tipo_escrito, version, editado_por_usuario, created_at, updated_at "
        "FROM defensia_escritos WHERE expediente_id = ? ORDER BY updated_at DESC",
        [exp_id],
    )

    return {
        "expediente": expediente,
        "documentos": [dict(r) for r in (docs_res.rows or [])] if docs_res else [],
        "briefs": [dict(r) for r in (briefs_res.rows or [])] if briefs_res else [],
        "dictamenes": [dict(r) for r in (dicts_res.rows or [])] if dicts_res else [],
        "escritos": [dict(r) for r in (escritos_res.rows or [])] if escritos_res else [],
    }


# ============================================================================
# Endpoint 5 — Upload documento
# ============================================================================


@router.post(
    "/expedientes/{exp_id}/documentos", status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_defensia_rate_limit("upload_documento"))
async def subir_documento(
    request: Request,
    exp_id: str,
    file: UploadFile = File(...),
    tipo_documento: Optional[str] = Form(default=None),
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    storage: DefensiaStorage = Depends(get_defensia_storage),
) -> dict[str, Any]:
    """Sube un documento a un expediente. NO dispara analisis juridico (Regla #1).

    La Fase 1 de extraccion tecnica puede disparase en un paso posterior del
    router de upload (cuando esten cableados los extractores), pero las
    fases 2-4 solo arrancan con ``POST /analyze``.
    """
    await _ensure_owner(db, exp_id, current_user.user_id)

    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="Fichero vacio")

    try:
        ciphertext, nonce = storage.cifrar(contenido)
    except DefensiaStorageUnavailable as exc:
        logger.warning("DefensIA upload: storage deshabilitado: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Servicio de almacenamiento DefensIA no disponible",
        ) from exc

    import hashlib

    doc_id = f"doc_{secrets.token_urlsafe(12)}"
    hash_sha256 = hashlib.sha256(contenido).hexdigest()
    # Ruta logica: prefijo ciphertext + nonce en base64 para simplificar v1.
    # En produccion real aparecera una ruta S3/Spaces aqui.
    import base64

    ruta_almacenada = (
        f"inline:{base64.b64encode(ciphertext).decode('ascii')}:"
        f"{base64.b64encode(nonce).decode('ascii')}"
    )

    tipo_doc_valor = tipo_documento or None
    if tipo_doc_valor:
        try:
            TipoDocumento(tipo_doc_valor)
        except ValueError:
            tipo_doc_valor = TipoDocumento.OTROS.value

    now = _now_iso()
    await db.execute(
        "INSERT INTO defensia_documentos "
        "(id, expediente_id, nombre_original, ruta_almacenada, mime_type, "
        "tamano_bytes, hash_sha256, tipo_documento, clasificacion_confianza, "
        "fecha_acto, datos_estructurados_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            doc_id,
            exp_id,
            file.filename or "documento",
            ruta_almacenada,
            file.content_type or "application/octet-stream",
            len(contenido),
            hash_sha256,
            tipo_doc_valor,
            None,
            None,
            None,
            now,
        ],
    )
    # Touch expediente updated_at
    await db.execute(
        "UPDATE defensia_expedientes SET updated_at = ? WHERE id = ?",
        [now, exp_id],
    )
    logger.info(
        "DefensIA: documento subido id=%s exp=%s bytes=%d",
        doc_id,
        exp_id,
        len(contenido),
    )
    return {
        "id": doc_id,
        "nombre_original": file.filename or "documento",
        "tipo_documento": tipo_doc_valor,
        "created_at": now,
    }


# ============================================================================
# Endpoints 6-8 — Brief CRUD
# ============================================================================


@router.post("/expedientes/{exp_id}/brief", status_code=status.HTTP_201_CREATED)
@limiter.limit(get_defensia_rate_limit("default"))
async def crear_brief(
    request: Request,
    exp_id: str,
    body: BriefRequest,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Crea (o anade) un brief al expediente. No reemplaza briefs previos."""
    await _ensure_owner(db, exp_id, current_user.user_id)

    brief_id = f"brief_{secrets.token_urlsafe(12)}"
    now = _now_iso()
    await db.execute(
        "INSERT INTO defensia_briefs (id, expediente_id, texto, chat_history_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [brief_id, exp_id, body.texto, None, now],
    )
    await db.execute(
        "UPDATE defensia_expedientes SET updated_at = ? WHERE id = ?",
        [now, exp_id],
    )
    return {"id": brief_id, "texto": body.texto, "created_at": now}


@router.get("/expedientes/{exp_id}/brief")
@limiter.limit(get_defensia_rate_limit("default"))
async def obtener_brief(
    request: Request,
    exp_id: str,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Devuelve el brief mas reciente del expediente."""
    await _ensure_owner(db, exp_id, current_user.user_id)
    brief = await _load_last_brief(db, exp_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief no encontrado")
    return {
        "id": brief.id,
        "texto": brief.texto,
        "chat_history": brief.chat_history,
    }


@router.put("/expedientes/{exp_id}/brief")
@limiter.limit(get_defensia_rate_limit("default"))
async def editar_brief(
    request: Request,
    exp_id: str,
    body: BriefRequest,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Reemplaza el texto del brief mas reciente (o crea uno si no hay)."""
    await _ensure_owner(db, exp_id, current_user.user_id)

    existing = await _load_last_brief(db, exp_id)
    now = _now_iso()
    if existing is None or existing.id is None:
        brief_id = f"brief_{secrets.token_urlsafe(12)}"
        await db.execute(
            "INSERT INTO defensia_briefs (id, expediente_id, texto, chat_history_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [brief_id, exp_id, body.texto, None, now],
        )
    else:
        brief_id = existing.id
        await db.execute(
            "UPDATE defensia_briefs SET texto = ? WHERE id = ?",
            [body.texto, brief_id],
        )
    await db.execute(
        "UPDATE defensia_expedientes SET updated_at = ? WHERE id = ?",
        [now, exp_id],
    )
    return {"id": brief_id, "texto": body.texto, "updated_at": now}


# ============================================================================
# Endpoint 9 — Analyze (SSE streaming)
# ============================================================================


@router.post("/expedientes/{exp_id}/analyze")
@limiter.limit(get_defensia_rate_limit("analyze"))
async def analizar_expediente(
    request: Request,
    exp_id: str,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    service: DefensiaService = Depends(get_defensia_service),
) -> EventSourceResponse:
    """Pipeline completo de analisis DefensIA en modo SSE.

    Eventos emitidos:
        - ``thinking``: estado intermedio ("detectando fase...").
        - ``fase``: ``{fase, confianza}``.
        - ``reglas``: ``{candidatos}``.
        - ``verificados``: ``{aceptados, descartados}``.
        - ``escrito_listo``: ``{escrito_id, length_chars}``.
        - ``done``: ``{dictamen_id, escrito_id, fase}``.
        - ``error``: ``{message}``.

    Traduce ``QuotaExcedida`` a HTTP 402 ANTES de abrir el stream SSE.
    """
    # Cargamos expediente + brief antes del stream para poder abortar con
    # HTTPException normales si faltan datos (Regla #1: brief obligatorio).
    exp_row = await _ensure_owner(db, exp_id, current_user.user_id)
    expediente = _row_a_expediente(exp_row)
    brief = await _load_last_brief(db, exp_id)
    if brief is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede analizar un expediente sin brief. Crea primero "
                "el brief con POST /expedientes/{id}/brief."
            ),
        )

    plan = await _resolver_plan_usuario(db, current_user.user_id)

    async def event_stream():
        try:
            yield {"event": "thinking", "data": "Detectando fase del procedimiento..."}

            # El facade hace todo el pipeline de una sola llamada. Para emitir
            # eventos intermedios granulares sin reescribirlo, apoyamos los
            # eventos en la respuesta final: "fase", "reglas", "verificados"
            # se emiten tras la llamada al facade con los datos del resultado.
            result = await service.analizar_expediente(
                expediente,
                brief,
                user_id=current_user.user_id,
                plan=plan,
                territory_filter=expediente.ccaa or None,
            )

            yield {
                "event": "fase",
                "data": json.dumps(
                    {
                        "fase": result["fase_detectada"],
                        "confianza": expediente.fase_confianza,
                    }
                ),
            }
            verificados = result.get("argumentos_verificados") or []
            descartados = int(result.get("argumentos_descartados_count") or 0)
            yield {
                "event": "reglas",
                "data": json.dumps(
                    {"candidatos": len(verificados) + descartados}
                ),
            }
            yield {
                "event": "verificados",
                "data": json.dumps(
                    {"aceptados": len(verificados), "descartados": descartados}
                ),
            }
            escrito_md = result.get("escrito_markdown") or ""
            yield {
                "event": "escrito_listo",
                "data": json.dumps(
                    {
                        "escrito_id": result.get("escrito_id"),
                        "length_chars": len(escrito_md),
                    }
                ),
            }

            # Marcar expediente como dictamen_listo
            await db.execute(
                "UPDATE defensia_expedientes "
                "SET estado = 'dictamen_listo', fase_detectada = ?, "
                "    fase_confianza = ?, updated_at = ? "
                "WHERE id = ?",
                [
                    result["fase_detectada"],
                    expediente.fase_confianza,
                    _now_iso(),
                    exp_id,
                ],
            )

            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "dictamen_id": result.get("dictamen_id"),
                        "escrito_id": result.get("escrito_id"),
                        "fase": result["fase_detectada"],
                    }
                ),
            }
        except QuotaExcedida as exc:
            logger.warning(
                "DefensIA analyze: cuota excedida user=%s plan=%s",
                current_user.user_id,
                plan,
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "code": "quota_excedida",
                        "message": str(exc),
                        "http_status": 402,
                    }
                ),
            }
            yield {"event": "done", "data": ""}
        except Exception as exc:  # noqa: BLE001
            logger.error("DefensIA analyze error: %s", exc, exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps(
                    {"code": "internal", "message": "Error procesando el analisis"}
                ),
            }
            yield {"event": "done", "data": ""}

    return EventSourceResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Endpoint 10 — GET dictamen
# ============================================================================


@router.get("/expedientes/{exp_id}/dictamen")
@limiter.limit(get_defensia_rate_limit("default"))
async def obtener_dictamen(
    request: Request,
    exp_id: str,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Devuelve el dictamen mas reciente del expediente."""
    await _ensure_owner(db, exp_id, current_user.user_id)

    result = await db.execute(
        "SELECT id, expediente_id, brief_id, fase_detectada, argumentos_json, "
        "resumen_caso, created_at, modelo_llm, tokens_consumidos "
        "FROM defensia_dictamenes "
        "WHERE expediente_id = ? ORDER BY created_at DESC LIMIT 1",
        [exp_id],
    )
    if not result or not getattr(result, "rows", None):
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")

    row = dict(result.rows[0])
    argumentos_raw = row.get("argumentos_json") or "[]"
    try:
        argumentos = (
            json.loads(argumentos_raw) if isinstance(argumentos_raw, str) else argumentos_raw
        )
    except json.JSONDecodeError:
        argumentos = []
    row["argumentos"] = argumentos
    row.pop("argumentos_json", None)
    return row


# ============================================================================
# Endpoint 11 — Export escrito (DOCX / PDF)
# ============================================================================


@router.get("/expedientes/{exp_id}/escrito/{escrito_id}/export")
@limiter.limit(get_defensia_rate_limit("default"))
async def exportar_escrito(
    request: Request,
    exp_id: str,
    escrito_id: str,
    format: str = Query(default="docx", pattern="^(docx|pdf)$"),
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    exporter: DefensiaExportService = Depends(get_defensia_export),
) -> Response:
    """Descarga el escrito como DOCX o PDF."""
    await _ensure_owner(db, exp_id, current_user.user_id)

    result = await db.execute(
        "SELECT id, tipo_escrito, contenido_markdown "
        "FROM defensia_escritos WHERE id = ? AND expediente_id = ?",
        [escrito_id, exp_id],
    )
    if not result or not getattr(result, "rows", None):
        raise HTTPException(status_code=404, detail="Escrito no encontrado")

    row = dict(result.rows[0])
    contenido_md = row.get("contenido_markdown") or ""
    tipo_escrito = row.get("tipo_escrito") or "escrito_defensia"

    if format == "docx":
        payload = exporter.markdown_a_docx(
            contenido_md, titulo=f"DefensIA - {tipo_escrito}"
        )
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"{tipo_escrito}-{escrito_id}.docx"
    else:
        payload = exporter.markdown_a_pdf(
            contenido_md, titulo=f"DefensIA - {tipo_escrito}"
        )
        media_type = "application/pdf"
        filename = f"{tipo_escrito}-{escrito_id}.pdf"

    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ============================================================================
# Endpoint 12 — PATCH escrito (edicion manual)
# ============================================================================


@router.patch("/expedientes/{exp_id}/escrito/{escrito_id}")
@limiter.limit(get_defensia_rate_limit("default"))
async def editar_escrito(
    request: Request,
    exp_id: str,
    escrito_id: str,
    body: EditarEscritoRequest,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Actualiza el contenido markdown del escrito e incrementa la version."""
    await _ensure_owner(db, exp_id, current_user.user_id)

    result = await db.execute(
        "SELECT id, version FROM defensia_escritos "
        "WHERE id = ? AND expediente_id = ?",
        [escrito_id, exp_id],
    )
    if not result or not getattr(result, "rows", None):
        raise HTTPException(status_code=404, detail="Escrito no encontrado")

    current_version = int(result.rows[0].get("version") or 1)
    new_version = current_version + 1
    now = _now_iso()

    await db.execute(
        "UPDATE defensia_escritos "
        "SET contenido_markdown = ?, version = ?, editado_por_usuario = 1, "
        "    updated_at = ? "
        "WHERE id = ? AND expediente_id = ?",
        [body.contenido_markdown, new_version, now, escrito_id, exp_id],
    )
    await db.execute(
        "UPDATE defensia_expedientes SET updated_at = ? WHERE id = ?",
        [now, exp_id],
    )
    return {"id": escrito_id, "version": new_version, "updated_at": now}


# ============================================================================
# Endpoint 13 — DELETE expediente (cascade)
# ============================================================================


@router.delete(
    "/expedientes/{exp_id}", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit(get_defensia_rate_limit("default"))
async def borrar_expediente(
    request: Request,
    exp_id: str,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> Response:
    """Borra el expediente. El FK ON DELETE CASCADE elimina documentos,
    briefs, dictamenes y escritos asociados.
    """
    await _ensure_owner(db, exp_id, current_user.user_id)
    await db.execute(
        "DELETE FROM defensia_expedientes WHERE id = ? AND user_id = ?",
        [exp_id, current_user.user_id],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Endpoint 14 — Chat SSE
# ============================================================================


@router.post("/chat")
@limiter.limit(get_defensia_rate_limit("chat"))
async def chat_defensia(
    request: Request,
    body: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
    agent=Depends(get_defensia_agent),
) -> EventSourceResponse:
    """Stream conversacional del DefensiaAgent.

    Eventos:
        - ``content``: chunk de texto.
        - ``done``: fin del stream.
    """

    async def event_stream():
        try:
            async for chunk in agent.chat_stream(
                body.message, chat_history=body.chat_history
            ):
                if chunk:
                    yield {"event": "content", "data": chunk}
            yield {"event": "done", "data": ""}
        except Exception as exc:  # noqa: BLE001
            logger.error("DefensIA chat error: %s", exc, exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": "Error en el chat DefensIA"}),
            }
            yield {"event": "done", "data": ""}

    return EventSourceResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Endpoint 15 — Estado de cuota
# ============================================================================


@router.get("/cuotas")
@limiter.limit(get_defensia_rate_limit("default"))
async def estado_cuotas(
    request: Request,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    quota: DefensiaQuotaService = Depends(get_defensia_quota_service),
) -> dict[str, Any]:
    """Devuelve el estado de cuota mensual del usuario para su plan."""
    plan = await _resolver_plan_usuario(db, current_user.user_id)
    estado = await quota._get_estado(current_user.user_id)  # noqa: SLF001
    limite = LIMITES_POR_PLAN.get(plan, 0)
    creados = int(estado.get("expedientes_creados") or 0)
    en_curso = int(estado.get("en_curso") or 0)
    disponibles = max(0, limite - creados - en_curso)
    precio_extra = PRECIO_EXTRA_POR_PLAN.get(plan, 0.0)
    return {
        "plan": plan,
        "limite": limite,
        "creados": creados,
        "en_curso": en_curso,
        "disponibles": disponibles,
        "precio_extra_eur": precio_extra,
    }
