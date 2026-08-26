"""Integración con Google Calendar v3 — reserva de citas con Joaquín.

Degrada con gracia en TODOS los puntos de fallo:
  - Sin ``CALENDAR_TOKEN_KEY`` / ``LEADBOT_CALENDAR_EMAIL`` → ``CalendarNotConfigured``.
  - Sin librerías ``google-api-python-client`` instaladas → ``CalendarNotConfigured``.
  - Sin refresh token en DB (OAuth grant pendiente) → ``CalendarNotConfigured``.

El agente captura ``CalendarNotConfigured`` y ofrece la vía alternativa
(recoger datos + que Joaquín contacte), de modo que el bot es 100% funcional
hoy y la reserva automática se "enciende" cuando se completa el grant OAuth.

La generación de huecos candidatos (``generate_candidate_slots``) es una función
PURA sin dependencia de Google — testeable de forma aislada.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.leadbot.config import LeadbotConfig, get_leadbot_config

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]

_WEEKDAY_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MONTH_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


class CalendarNotConfigured(Exception):
    """Calendar no disponible (sin config, sin libs o sin grant OAuth)."""


def _parse_hhmm(value: str) -> time:
    hh, _, mm = value.partition(":")
    return time(int(hh), int(mm or 0))


def humanize_slot(dt: datetime) -> str:
    """'lunes 16 de junio a las 10:30' (español, hora local)."""
    return (
        f"{_WEEKDAY_ES[dt.weekday()]} {dt.day} de {_MONTH_ES[dt.month - 1]} "
        f"a las {dt.strftime('%H:%M')}"
    )


def generate_candidate_slots(cfg: LeadbotConfig, now: datetime, limit: int = 60) -> list[datetime]:
    """Genera huecos candidatos (tz-aware) según la config de disponibilidad.

    No consulta Google: sólo aplica días/ventanas/duración/horizonte. El
    filtrado contra ocupación real lo hace ``CalendarService.get_free_slots``.
    """
    tz = ZoneInfo(cfg.timezone)
    now = now.astimezone(tz)
    step = max(cfg.slot_minutes, 5)
    slots: list[datetime] = []
    for day_offset in range(cfg.booking_horizon_days + 1):
        day = (now + timedelta(days=day_offset)).date()
        if day.weekday() not in cfg.work_days:
            continue
        for win_start, win_end in cfg.work_windows:
            try:
                start_t, end_t = _parse_hhmm(win_start), _parse_hhmm(win_end)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Ventana horaria inválida (LEADBOT_WORK_HOURS): %r-%r", win_start, win_end
                )
                continue
            cursor = datetime.combine(day, start_t, tzinfo=tz)
            window_end = datetime.combine(day, end_t, tzinfo=tz)
            while cursor + timedelta(minutes=cfg.slot_minutes) <= window_end:
                if cursor > now + timedelta(minutes=cfg.buffer_minutes):
                    slots.append(cursor)
                    if len(slots) >= limit:
                        return slots
                cursor += timedelta(minutes=step)
    return slots


class CalendarService:
    def __init__(self, repo, cfg: LeadbotConfig | None = None):
        self.repo = repo
        self.cfg = cfg or get_leadbot_config()

    def _ensure_configured(self) -> None:
        if not self.cfg.calendar_configured:
            raise CalendarNotConfigured("CALENDAR_TOKEN_KEY o LEADBOT_CALENDAR_EMAIL ausentes")
        if not (self.cfg.google_oauth_client_id and self.cfg.google_oauth_client_secret):
            raise CalendarNotConfigured("GOOGLE_OAUTH_CLIENT_ID/SECRET ausentes")

    async def _build_service(self):
        self._ensure_configured()
        cred_row = await self.repo.get_oauth_credential(self.cfg.calendar_account_email)
        if not cred_row:
            raise CalendarNotConfigured("Refresh token no encontrado — grant OAuth pendiente")
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            from app.leadbot.crypto import decrypt_token
        except ImportError as exc:
            raise CalendarNotConfigured(f"Librerías Google no instaladas: {exc}") from exc

        refresh_token = decrypt_token(cred_row["refresh_token_encrypted"])
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.cfg.google_oauth_client_id,
            client_secret=self.cfg.google_oauth_client_secret,
            scopes=CALENDAR_SCOPES,
        )
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    async def get_free_slots(self, max_slots: int = 6) -> list[dict]:
        """Devuelve huecos libres ``[{iso, human}]`` cruzando candidatos × ocupación."""
        tz = ZoneInfo(self.cfg.timezone)
        now = datetime.now(tz)
        candidates = generate_candidate_slots(self.cfg, now)
        if not candidates:
            return []

        service = await self._build_service()  # raises CalendarNotConfigured si procede
        time_min = candidates[0].isoformat()
        time_max = (candidates[-1] + timedelta(minutes=self.cfg.slot_minutes)).isoformat()

        def _freebusy():
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": self.cfg.timezone,
                "items": [{"id": self.cfg.calendar_account_email}],
            }
            resp = service.freebusy().query(body=body).execute()
            cal = resp.get("calendars", {}).get(self.cfg.calendar_account_email, {})
            return cal.get("busy", [])

        busy_raw = await asyncio.to_thread(_freebusy)
        busy = [
            (datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])) for b in busy_raw
        ]
        buf = timedelta(minutes=self.cfg.buffer_minutes)
        dur = timedelta(minutes=self.cfg.slot_minutes)

        free: list[dict] = []
        for slot in candidates:
            s_start, s_end = slot - buf, slot + dur + buf
            if any(s_start < b_end and b_start < s_end for b_start, b_end in busy):
                continue
            free.append({"iso": slot.isoformat(), "human": humanize_slot(slot)})
            if len(free) >= max_slots:
                break
        return free

    async def create_event(self, slot_iso: str, attendee_email: str, attendee_name: str) -> dict:
        """Crea el evento con Google Meet. Devuelve ``{event_id, html_link, meet_link}``."""
        service = await self._build_service()
        start = datetime.fromisoformat(slot_iso)
        end = start + timedelta(minutes=self.cfg.slot_minutes)
        summary = f"Reunión {self.cfg.brand_name} — {attendee_name or attendee_email}"

        def _insert():
            event = {
                "summary": summary,
                "description": (
                    f"Cita solicitada vía el asistente de {self.cfg.brand_name}.\n"
                    f"Contacto: {attendee_name} <{attendee_email}>"
                ),
                "start": {"dateTime": start.isoformat(), "timeZone": self.cfg.timezone},
                "end": {"dateTime": end.isoformat(), "timeZone": self.cfg.timezone},
                "attendees": [{"email": attendee_email}],
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"leadbot-{int(start.timestamp())}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
                "reminders": {"useDefault": True},
            }
            return (
                service.events()
                .insert(
                    calendarId=self.cfg.calendar_account_email,
                    body=event,
                    conferenceDataVersion=1,
                    sendUpdates="all",
                )
                .execute()
            )

        created = await asyncio.to_thread(_insert)
        meet_link = None
        for ep in created.get("conferenceData", {}).get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri")
                break
        return {
            "event_id": created.get("id"),
            "html_link": created.get("htmlLink"),
            "meet_link": meet_link,
        }
