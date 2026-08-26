"""Modelos Pydantic del leadbot (request/response de la API pública)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class StartRequest(BaseModel):
    """Arranque de conversación. GDPR + Turnstile + honeypot."""

    gdpr_consent: bool = Field(..., description="Checkbox de consentimiento RGPD (obligatorio)")
    turnstile_token: str | None = Field(default=None, description="Token Cloudflare Turnstile")
    # Honeypot: campo oculto que un humano nunca rellena. Si llega con valor → bot.
    website: str | None = Field(default=None, description="Honeypot — debe ir vacío")


class StartResponse(BaseModel):
    conversation_id: str
    lead_id: str
    greeting: str


class MessageRequest(BaseModel):
    """Turno de usuario en la conversación."""

    conversation_id: str = Field(..., min_length=8, max_length=64)
    message: str = Field(..., min_length=1, max_length=2000)
    # Cuando el usuario pulsa un chip de hueco, el frontend manda su ISO para que
    # el agente pueda reservarlo (el texto visible es legible para humanos).
    selected_slot_iso: str | None = Field(default=None, max_length=64)


class ForgetRequest(BaseModel):
    """RGPD Art. 17 — derecho al olvido."""

    email: EmailStr


class LeadOut(BaseModel):
    """Vista de un lead para el dashboard owner-only."""

    id: str
    status: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    sector: str | None = None
    need: str | None = None
    decision_maker: int | None = None
    timeline: str | None = None
    budget_range: str | None = None
    booking_slot: str | None = None
    calendar_event_id: str | None = None
    transcript_summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
