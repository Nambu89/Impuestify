"""Ejecutores de las herramientas del LeadAgent (efectos secundarios).

El agente (``agent.py``) sólo conoce la interfaz ``dispatch(name, args)`` — toda
la lógica con efectos (persistir lead, consultar calendar, enviar email) vive
aquí, lo que mantiene el agente testeable con un dispatcher mock.

Captura el estado de efectos (slots ofrecidos, reserva, escalado) para que el
router lo exponga al frontend (chips de huecos, confirmación, etc.).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.leadbot.calendar_service import CalendarNotConfigured, CalendarService, humanize_slot
from app.leadbot.config import LeadbotConfig, get_leadbot_config
from app.leadbot.email_service import LeadbotEmailService
from app.leadbot.enrich import LeadEnricher
from app.leadbot.repository import LeadRepository

logger = logging.getLogger(__name__)

_TIMELINE = {"now", "1-3m", "3-6m", "6m+"}
# Rangos pensados para autónomos/PYMES pequeñas de Melilla (no enterprise).
_BUDGET = {"<500", "500-1500", "1500-3000", "3000+"}


class LeadToolContext:
    """Dispatcher de herramientas para un turno de conversación concreto."""

    def __init__(
        self,
        repo: LeadRepository,
        lead_id: str,
        conversation_id: str,
        confirm_base_url: str,
        calendar: CalendarService | None = None,
        email: LeadbotEmailService | None = None,
        enricher: LeadEnricher | None = None,
        cfg: LeadbotConfig | None = None,
    ):
        self.repo = repo
        self.lead_id = lead_id
        self.conversation_id = conversation_id
        self.confirm_base_url = confirm_base_url.rstrip("/")
        self.cfg = cfg or get_leadbot_config()
        self.calendar = calendar or CalendarService(repo, self.cfg)
        self.email = email or LeadbotEmailService(self.cfg)
        self.enricher = enricher or LeadEnricher(self.cfg)
        # Estado de efectos para el frontend / router
        self.offered_slots: list[dict] = []
        self.booking: dict | None = None
        self.escalated = False
        self.lead_updates: dict = {}
        self._owner_alerted = False

    # ------------------------------------------------------------------ dispatch
    async def dispatch(self, name: str, args: dict[str, Any]) -> dict:
        try:
            if name == "save_lead_info":
                return await self._save_lead_info(args)
            if name == "get_available_slots":
                return await self._get_available_slots(args)
            if name == "book_meeting":
                return await self._book_meeting(args)
            if name == "escalate_to_human":
                return await self._escalate_to_human(args)
        except Exception as exc:  # noqa: BLE001 — nunca romper el loop del agente
            logger.error("Leadbot tool %s failed: %s", name, exc, exc_info=True)
            return {"ok": False, "error": "internal_error"}
        return {"ok": False, "error": f"herramienta desconocida: {name}"}

    # -------------------------------------------------------------------- tools
    async def _save_lead_info(self, args: dict) -> dict:
        updates: dict = {}
        for key in ("name", "email", "phone", "company", "sector", "need"):
            val = args.get(key)
            if isinstance(val, str) and val.strip():
                updates[key] = val.strip()[:500]
        if isinstance(args.get("decision_maker"), bool):
            updates["decision_maker"] = 1 if args["decision_maker"] else 0
        if args.get("timeline") in _TIMELINE:
            updates["timeline"] = args["timeline"]
        if args.get("budget_range") in _BUDGET:
            updates["budget_range"] = args["budget_range"]

        if updates:
            # Marca como cualificado en cuanto tengamos necesidad + email.
            current = await self.repo.get_lead(self.lead_id) or {}
            has_email = updates.get("email") or current.get("email")
            has_need = updates.get("need") or current.get("need")
            if has_email and has_need and (current.get("status") in (None, "new")):
                updates["status"] = "qualified"
            await self.repo.update_lead(self.lead_id, **updates)
            self.lead_updates.update(updates)
        return {"ok": True, "saved_fields": sorted(updates.keys())}

    async def _get_available_slots(self, args: dict) -> dict:
        try:
            slots = await self.calendar.get_free_slots(max_slots=6)
        except CalendarNotConfigured as exc:
            logger.info("Calendar no disponible: %s", exc)
            return {
                "available": False,
                "reason": "calendar_unavailable",
                "instruction": (
                    "La reserva automática no está disponible ahora mismo. Pide al "
                    "usuario su email (y teléfono si quiere) y dile que el equipo le "
                    "contactará para fijar la cita. Llama luego a book_meeting con el "
                    "email para registrar el lead."
                ),
            }
        if not slots:
            return {
                "available": True,
                "slots": [],
                "note": "Sin huecos en el horizonte configurado",
            }
        self.offered_slots = slots
        return {"available": True, "slots": slots}

    async def _book_meeting(self, args: dict) -> dict:
        email = (args.get("attendee_email") or "").strip()
        name = (args.get("attendee_name") or "").strip()
        slot_iso = (args.get("slot_iso") or "").strip()

        if not email or "@" not in email:
            return {"ok": False, "error": "missing_email", "instruction": "Pide el email primero."}

        await self.repo.update_lead(self.lead_id, email=email, name=name or None)

        # --- Vía degradada: calendar no configurado → lead cualificado + aviso ---
        if not self.cfg.calendar_configured:
            await self.repo.update_lead(self.lead_id, status="qualified")
            await self._alert_owner()
            self.booking = {"status": "pending_human", "slot_iso": slot_iso or None}
            return {
                "ok": True,
                "calendar_unavailable": True,
                "message": "Lead registrado. El equipo contactará por email para fijar la cita.",
            }

        if not slot_iso:
            return {
                "ok": False,
                "error": "missing_slot",
                "instruction": "Llama antes a get_available_slots y pide al usuario que elija un hueco.",
            }

        try:
            human = humanize_slot(datetime.fromisoformat(slot_iso))
        except (ValueError, TypeError):
            return {"ok": False, "error": "invalid_slot"}

        # --- Magic-link: confirmar email antes de crear el evento (anti-spam) ---
        if self.cfg.require_magic_link:
            token = await self.repo.create_verification(self.lead_id, slot_iso, email, name)
            confirm_url = f"{self.confirm_base_url}/api/lead-chat/confirm/{token}"
            sent = await self.email.send_magic_link(email, name, human, confirm_url)
            self.booking = {"status": "pending_confirmation", "slot_iso": slot_iso, "human": human}
            return {
                "ok": True,
                "pending_confirmation": True,
                "email_sent": sent,
                "message": (
                    f"Hueco {human} reservado provisionalmente. Se ha enviado un email a "
                    f"{email} para confirmar (caduca en 30 min)."
                ),
            }

        # --- Reserva directa (sin magic-link) ---
        event = await self.calendar.create_event(slot_iso, email, name)
        await self.repo.update_lead(
            self.lead_id,
            status="booked",
            calendar_event_id=event.get("event_id"),
            booking_slot=slot_iso,
        )
        await self.email.send_booking_confirmation(email, name, human, event.get("meet_link"))
        await self._alert_owner()
        self.booking = {"status": "booked", "slot_iso": slot_iso, "human": human, **event}
        return {"ok": True, "booked": True, "human": human, "meet_link": event.get("meet_link")}

    async def _escalate_to_human(self, args: dict) -> dict:
        reason = (args.get("reason") or "")[:300]
        await self._alert_owner()
        self.escalated = True
        return {
            "ok": True,
            "message": (
                f"El equipo de {self.cfg.brand_name} se pondrá en contacto. "
                "Asegúrate de tener el email del usuario guardado."
            ),
            "reason": reason,
        }

    # ------------------------------------------------------------------ helpers
    async def _alert_owner(self) -> None:
        if self._owner_alerted:
            return
        lead = await self.repo.get_lead(self.lead_id)
        if not lead:
            return
        # Enriquecimiento: la IA sintetiza la conversación en un brief accionable
        # para Joaquín antes de mandar el aviso. Best-effort (cae a brief básico).
        messages = await self.repo.get_messages(self.conversation_id, limit=50)
        brief = await self.enricher.build_brief(lead, messages)
        if brief:
            await self.repo.update_lead(self.lead_id, transcript_summary=brief)
            lead = {**lead, "transcript_summary": brief}
        await self.email.send_lead_alert_to_owner(lead, brief=brief)
        self._owner_alerted = True
