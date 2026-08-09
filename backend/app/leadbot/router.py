"""Endpoints públicos del leadbot + admin owner-only.

Montados en ``main.py`` SÓLO si ``settings.LEADBOT_ENABLED`` (defensa en
profundidad: con la bandera apagada este módulo ni se importa, así que las rutas
no pueden exponerse por accidente).

Seguridad del chat público:
  - Turnstile (reusa ``verify_turnstile`` de auth) + honeypot + consentimiento RGPD.
  - Rate limit per-IP (slowapi) + cap de tokens diario per-IP.
  - Pipeline de seguridad SIN capa PII (el bot recoge email/teléfono a propósito)
    ni clasificador fiscal (el bot no es fiscal): sólo sanitización + inyección + SQLi.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from app.auth.jwt_handler import TokenData
from app.auth.owner_guard import require_owner
from app.config import settings
from app.database.turso_client import TursoClient
from app.leadbot.agent import LeadAgent
from app.leadbot.calendar_service import CalendarNotConfigured, CalendarService, humanize_slot
from app.leadbot.config import get_leadbot_config
from app.leadbot.email_service import LeadbotEmailService
from app.leadbot.models import ForgetRequest, LeadOut, MessageRequest, StartRequest, StartResponse
from app.leadbot.repository import LeadRepository, hash_ip
from app.leadbot.tools import LeadToolContext
from app.security.rate_limiter import limiter
from app.security.security_pipeline import SecurityPipeline

logger = logging.getLogger(__name__)

# Pipeline a medida para el leadbot: SIN PII (recoge email a propósito) y SIN
# clasificador fiscal (el bot no es fiscal). Conserva sanitización + inyección + SQLi.
_lead_security = SecurityPipeline(enable_pii=False, enable_topic_classifier=False)

chat_router = APIRouter(prefix="/api/lead-chat", tags=["leadbot"])
leads_router = APIRouter(prefix="/api/leads", tags=["leadbot"])


async def get_db(request: Request) -> TursoClient:
    db = getattr(request.app.state, "db_client", None)
    if not db:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return db


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _confirm_base_url(request: Request) -> str:
    return os.environ.get("LEADBOT_PUBLIC_BASE_URL") or str(request.base_url)


def _sse(event: str, data) -> dict:
    return {
        "event": event,
        "data": data if isinstance(data, str) else json.dumps(data, ensure_ascii=False),
    }


# ============================================================ START
@chat_router.post("/start", response_model=StartResponse)
@limiter.limit("8/minute")
async def start_conversation(
    request: Request, body: StartRequest, db: TursoClient = Depends(get_db)
):
    """Arranca una conversación: valida RGPD + Turnstile + honeypot, crea el lead."""
    # Honeypot: si el campo oculto llega relleno, es un bot.
    if body.website:
        logger.info("Leadbot honeypot disparado — petición descartada")
        raise HTTPException(status_code=400, detail="Solicitud no válida")

    if not body.gdpr_consent:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar la política de privacidad para usar el asistente.",
        )

    # Turnstile (reusa la verificación de auth). Sólo exige token si hay secret.
    from app.routers.auth import verify_turnstile

    if body.turnstile_token:
        if not await verify_turnstile(body.turnstile_token, _client_ip(request)):
            raise HTTPException(status_code=400, detail="Verificación de seguridad fallida.")
    elif settings.TURNSTILE_SECRET_KEY:
        raise HTTPException(status_code=400, detail="Verificación de seguridad requerida.")

    repo = LeadRepository(db)
    conversation_id = uuid.uuid4().hex
    from datetime import UTC, datetime

    lead_id = await repo.create_lead(
        conversation_id=conversation_id,
        gdpr_consent_at=datetime.now(UTC).isoformat(),
        ip_hash=hash_ip(_client_ip(request)),
    )
    await repo.add_usage(hash_ip(_client_ip(request)), 0, 0, new_conversation=True)

    cfg = get_leadbot_config()
    greeting = (
        f"¡Hola! 👋 Soy el asistente virtual de {cfg.brand_name}. "
        "Te ayudo a resolver dudas y, si quieres, agendamos una llamada con el equipo. "
        "¿En qué estáis pensando o qué te gustaría automatizar?"
    )
    return StartResponse(conversation_id=conversation_id, lead_id=lead_id, greeting=greeting)


# ============================================================ MESSAGE (SSE)
@chat_router.post("/message")
@limiter.limit("20/minute")
async def send_message(request: Request, body: MessageRequest, db: TursoClient = Depends(get_db)):
    """Procesa un turno del usuario y devuelve la respuesta vía SSE."""
    repo = LeadRepository(db)
    lead = await repo.get_lead_by_conversation(body.conversation_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Conversación no encontrada. Reinicia el chat.")

    cfg = get_leadbot_config()
    ip_hash = hash_ip(_client_ip(request))

    async def stream():
        # Cap de longitud de conversación (anti-abuso)
        if await repo.count_messages(body.conversation_id) >= cfg.max_messages_per_conversation:
            yield _sse(
                "content",
                "Hemos llegado al límite de esta conversación. Si quieres, déjanos tu "
                "email y el equipo te contactará. 🙌",
            )
            yield _sse("done", {"conversation_id": body.conversation_id})
            return

        # Cap de tokens diario per-IP
        usage = await repo.get_usage_today(ip_hash)
        if (usage.get("tokens_in", 0) + usage.get("tokens_out", 0)) >= cfg.daily_token_cap_per_ip:
            yield _sse(
                "content",
                "Has alcanzado el límite de uso por hoy. Vuelve mañana o escríbenos a "
                f"{cfg.smtp_from_email}. 🙏",
            )
            yield _sse("done", {"conversation_id": body.conversation_id})
            return

        # Seguridad (sanitización + inyección + SQLi). Sin PII / sin topic fiscal.
        check = _lead_security.check(body.message, user_id=body.conversation_id)
        if not check.is_safe:
            await repo.add_message(body.conversation_id, "user", body.message[:2000])
            yield _sse(
                "content",
                "No he podido procesar ese mensaje. Cuéntame con tus palabras qué "
                "necesitas y seguimos. 🙂",
            )
            yield _sse("done", {"conversation_id": body.conversation_id, "blocked": True})
            return

        user_text = check.sanitized_text or body.message
        # Guardamos el texto legible; al agente le pasamos además el ISO del hueco
        # elegido (si lo hay) para que pueda reservarlo sin inventarlo.
        await repo.add_message(body.conversation_id, "user", user_text)
        history = await repo.get_messages(body.conversation_id, limit=30)
        agent_input = user_text
        if body.selected_slot_iso:
            agent_input = f"{user_text}\n[slot_iso seleccionado: {body.selected_slot_iso}]"

        yield _sse("thinking", "…")

        dispatcher = LeadToolContext(
            repo=repo,
            lead_id=lead["id"],
            conversation_id=body.conversation_id,
            confirm_base_url=_confirm_base_url(request),
            cfg=cfg,
        )
        agent = LeadAgent(cfg=cfg)
        result = await agent.run(agent_input, history, dispatcher)

        await repo.add_message(body.conversation_id, "assistant", result.reply_text)
        await repo.add_usage(ip_hash, result.tokens_in, result.tokens_out)

        yield _sse("content", result.reply_text)
        if dispatcher.offered_slots:
            yield _sse("meta", {"type": "slots", "slots": dispatcher.offered_slots})
        if dispatcher.booking:
            yield _sse("meta", {"type": "booking", "booking": dispatcher.booking})
        yield _sse("done", {"conversation_id": body.conversation_id})

    return EventSourceResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================================ CONFIRM (magic-link)
@chat_router.get("/confirm/{token}", response_class=HTMLResponse)
async def confirm_booking(token: str, request: Request, db: TursoClient = Depends(get_db)):
    """Confirma una cita vía magic-link: crea el evento real en Calendar."""
    cfg = get_leadbot_config()
    repo = LeadRepository(db)
    verif = await repo.get_verification(token)

    def _page(title: str, body: str) -> str:
        return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{cfg.brand_name}</title></head>
<body style="font-family:-apple-system,Segoe UI,sans-serif;background:#faf7f2;margin:0;padding:40px">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)">
<div style="background:#1e40af;color:#fff;padding:24px"><h1 style="margin:0;font-size:20px">{cfg.brand_name}</h1></div>
<div style="padding:28px;color:#1f2937"><h2 style="margin-top:0">{title}</h2>{body}</div>
</div></body></html>"""

    from datetime import UTC, datetime

    if not verif:
        return HTMLResponse(
            _page("Enlace no válido", "<p>Este enlace de confirmación no existe.</p>"),
            status_code=404,
        )
    if verif.get("consumed_at"):
        return HTMLResponse(
            _page("Ya confirmada", "<p>Esta cita ya estaba confirmada. ¡Nos vemos!</p>")
        )
    try:
        expired = datetime.fromisoformat(verif["expires_at"]) < datetime.now(UTC)
    except (ValueError, TypeError):
        expired = True
    if expired:
        return HTMLResponse(
            _page(
                "Enlace caducado",
                "<p>El enlace ha caducado. Vuelve al chat para pedir un nuevo hueco.</p>",
            ),
            status_code=410,
        )

    lead_id = verif["lead_id"]
    slot_iso = verif["slot_iso"]
    email = verif["attendee_email"]
    name = verif.get("attendee_name") or ""
    human = humanize_slot(datetime.fromisoformat(slot_iso)) if slot_iso else ""
    calendar = CalendarService(repo, cfg)
    emailer = LeadbotEmailService(cfg)

    try:
        event = await calendar.create_event(slot_iso, email, name)
        await repo.update_lead(
            lead_id,
            status="booked",
            calendar_event_id=event.get("event_id"),
            booking_slot=slot_iso,
        )
        await repo.consume_verification(token)
        await emailer.send_booking_confirmation(email, name, human, event.get("meet_link"))
        lead = await repo.get_lead(lead_id)
        if lead:
            await emailer.send_lead_alert_to_owner(lead)
        meet = (
            f'<p>Enlace de la videollamada: <a href="{event.get("meet_link")}">{event.get("meet_link")}</a></p>'
            if event.get("meet_link")
            else ""
        )
        return HTMLResponse(
            _page(
                "✅ Cita confirmada",
                f"<p>Tu cita queda confirmada para el <strong>{human}</strong>.</p>{meet}<p>Te hemos enviado un email con los detalles.</p>",
            )
        )
    except CalendarNotConfigured:
        # No hay calendar: registramos como cualificado y avisamos al equipo.
        await repo.update_lead(lead_id, status="qualified")
        await repo.consume_verification(token)
        lead = await repo.get_lead(lead_id)
        if lead:
            await emailer.send_lead_alert_to_owner(lead)
        return HTMLResponse(
            _page(
                "Solicitud recibida",
                "<p>Hemos recibido tu solicitud. El equipo te contactará por email para fijar la cita.</p>",
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Confirm booking error: %s", exc, exc_info=True)
        return HTMLResponse(
            _page(
                "Algo ha fallado",
                "<p>No hemos podido confirmar la cita. Inténtalo de nuevo o escríbenos.</p>",
            ),
            status_code=500,
        )


# ============================================================ GDPR forget
@leads_router.post("/forget")
@limiter.limit("3/minute")
async def forget_lead(request: Request, body: ForgetRequest, db: TursoClient = Depends(get_db)):
    """RGPD Art. 17 — borra todos los datos asociados a un email."""
    repo = LeadRepository(db)
    deleted = await repo.delete_by_email(str(body.email))
    return {"ok": True, "deleted": deleted}


# ============================================================ Admin (owner-only)
@leads_router.get("", response_model=list[LeadOut])
async def list_leads(
    db: TursoClient = Depends(get_db),
    status: str | None = None,
    limit: int = 200,
    _owner: TokenData = Depends(require_owner),
):
    """Lista de leads para el dashboard del propietario."""
    repo = LeadRepository(db)
    rows = await repo.list_leads(status=status, limit=limit)
    return [LeadOut(**{k: row.get(k) for k in LeadOut.model_fields}) for row in rows]
