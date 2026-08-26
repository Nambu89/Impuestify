"""Envío de email del leadbot vía SMTP del dominio (SiteGround).

Usa ``smtplib`` de la stdlib envuelto en ``asyncio.to_thread`` para no bloquear
el event loop — evita añadir ``aiosmtplib`` como dependencia. Degrada con
gracia: si SMTP no está configurado, loguea y devuelve ``False`` (el flujo del
bot sigue funcionando, simplemente no manda el correo).

NO se reutiliza el ``EmailService`` de Impuestify (Resend) a propósito: el
dominio ``iamelilla.com`` tiene su email en SiteGround y queremos aislamiento
total respecto a la infraestructura de email de Impuestify.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.leadbot.config import LeadbotConfig, get_leadbot_config

logger = logging.getLogger(__name__)


def _send_sync(cfg: LeadbotConfig, to: str, subject: str, html: str, text: str) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg.smtp_from_name, cfg.smtp_from_email))
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        if cfg.smtp_use_ssl:
            with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
                server.login(cfg.smtp_user, cfg.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
                server.starttls()
                server.login(cfg.smtp_user, cfg.smtp_password)
                server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 — nunca romper el flujo del bot
        logger.error("Leadbot SMTP send failed to=%s subject=%r: %s", to, subject, exc)
        return False


def _shell(cfg: LeadbotConfig, title: str, body_html: str) -> str:
    return f"""\
<div style="font-family:-apple-system,Segoe UI,sans-serif;max-width:600px;margin:0 auto">
  <div style="background:#1e40af;color:#fff;padding:20px;border-radius:8px 8px 0 0">
    <h1 style="margin:0;font-size:20px">{cfg.brand_name}</h1>
    <p style="margin:4px 0 0;opacity:.9;font-size:14px">{title}</p>
  </div>
  <div style="background:#faf7f2;padding:24px;border-radius:0 0 8px 8px;color:#1f2937">
    {body_html}
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0">
    <p style="color:#6b7280;font-size:12px">
      Mensaje automático de {cfg.brand_name}. Asistente de IA — no es asesoramiento
      vinculante. Puedes solicitar la baja de tus datos respondiendo a este correo.
    </p>
  </div>
</div>"""


class LeadbotEmailService:
    def __init__(self, cfg: LeadbotConfig | None = None):
        self.cfg = cfg or get_leadbot_config()

    @property
    def configured(self) -> bool:
        return self.cfg.smtp_configured

    async def _send(self, to: str, subject: str, html: str, text: str) -> bool:
        if not self.configured:
            logger.warning("Leadbot SMTP no configurado — email a %r NO enviado (%s)", to, subject)
            return False
        return await asyncio.to_thread(_send_sync, self.cfg, to, subject, html, text)

    async def send_magic_link(self, to: str, name: str, slot_human: str, confirm_url: str) -> bool:
        subject = f"Confirma tu cita con {self.cfg.brand_name}"
        body = (
            f"<p>Hola{(' ' + name) if name else ''},</p>"
            f"<p>Para confirmar tu cita del <strong>{slot_human}</strong>, "
            f"pulsa el botón (caduca en 30 minutos):</p>"
            f'<p style="text-align:center;margin:24px 0">'
            f'<a href="{confirm_url}" style="background:#06b6d4;color:#fff;'
            f'padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600">'
            f"Confirmar cita</a></p>"
            f'<p style="font-size:13px;color:#6b7280">Si no has solicitado esta cita, ignora este correo.</p>'
        )
        text = f"Confirma tu cita del {slot_human}: {confirm_url}"
        return await self._send(to, subject, _shell(self.cfg, "Confirma tu cita", body), text)

    async def send_lead_alert_to_owner(self, lead: dict, brief: str | None = None) -> bool:
        owner = self.cfg.owner_notify_email
        if not owner:
            logger.warning("LEADBOT_OWNER_NOTIFY_EMAIL no configurado — alerta de lead no enviada")
            return False

        # Brief enriquecido por la IA (lo más útil para Joaquín) — arriba del todo.
        brief = brief or lead.get("transcript_summary") or ""
        brief_html = ""
        if brief:
            import html as _html

            brief_html = (
                '<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;'
                'padding:16px;margin:0 0 16px;white-space:pre-wrap;font-size:14px;line-height:1.5">'
                f"{_html.escape(brief)}</div>"
            )

        rows = "".join(
            f'<tr><td style="padding:4px 8px;color:#6b7280">{label}</td>'
            f'<td style="padding:4px 8px"><strong>{lead.get(key) or "—"}</strong></td></tr>'
            for label, key in [
                ("Nombre", "name"),
                ("Email", "email"),
                ("Teléfono", "phone"),
                ("Negocio", "company"),
                ("Sector", "sector"),
                ("Necesidad", "need"),
                ("Plazo", "timeline"),
                ("Presupuesto", "budget_range"),
                ("Cita", "booking_slot"),
                ("Estado", "status"),
            ]
        )
        body = (
            "<p><strong>Resumen del posible cliente:</strong></p>"
            f"{brief_html}"
            '<p style="color:#6b7280;font-size:13px;margin:16px 0 4px">Datos en bruto:</p>'
            f'<table style="border-collapse:collapse;width:100%">{rows}</table>'
        )
        text = (
            (brief or "Nuevo lead")
            + "\n\n"
            + ", ".join(
                f"{k}={lead.get(k)}"
                for k in ("name", "email", "phone", "company", "need", "timeline", "budget_range")
            )
        )
        subject = f"🔔 Nuevo lead — {lead.get('name') or lead.get('company') or lead.get('email') or 'sin nombre'}"
        return await self._send(owner, subject, _shell(self.cfg, "Nuevo lead", body), text)

    async def send_booking_confirmation(
        self, to: str, name: str, slot_human: str, meet_link: str | None
    ) -> bool:
        link_html = (
            f'<p>Enlace de la videollamada: <a href="{meet_link}">{meet_link}</a></p>'
            if meet_link
            else ""
        )
        body = (
            f"<p>Hola{(' ' + name) if name else ''},</p>"
            f"<p>Tu cita queda confirmada para el <strong>{slot_human}</strong>.</p>"
            f"{link_html}"
            f"<p>Si necesitas cambiarla, responde a este correo.</p>"
        )
        text = f"Cita confirmada: {slot_human}. {meet_link or ''}"
        subject = f"✅ Cita confirmada con {self.cfg.brand_name}"
        return await self._send(to, subject, _shell(self.cfg, "Cita confirmada", body), text)
