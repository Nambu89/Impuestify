"""Leadbot configuration — env-driven, ISOLATED from app/config.py.

Lee variables de entorno propias (prefijo ``LEADBOT_`` o ``SMTP_``) para no
tocar el ``Settings`` global de Impuestify. Todas tienen valor por defecto
seguro para que el módulo importe sin reventar incluso sin configurar nada
(las features que requieran credenciales degradan con gracia).

Los valores de horario (LEADBOT_WORK_*) son provisionales hasta que Joaquín
confirme su disponibilidad real — se cambian por env tras la reunión, sin tocar
código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get(key: str, default: str = "") -> str:
    val = os.environ.get(key)
    return val.strip() if isinstance(val, str) else default


def _get_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _parse_days(raw: str, default: list[int]) -> list[int]:
    """Días laborables como ``date.weekday()`` (lunes=0 … domingo=6)."""
    if not raw:
        return default
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 0 <= int(part) <= 6:
            out.append(int(part))
    return out or default


def _parse_windows(raw: str, default: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Ventanas horarias ``"10:00-14:00,17:00-20:00"`` -> [("10:00","14:00"), ...]."""
    if not raw:
        return default
    out: list[tuple[str, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            start, end = start.strip(), end.strip()
            if start and end:
                out.append((start, end))
    return out or default


@dataclass(frozen=True)
class LeadbotConfig:
    # --- OpenAI (el agente) ---
    openai_api_key: str = ""
    model: str = "gpt-5-mini"
    reasoning_effort: str = "minimal"
    max_completion_tokens: int = 1200
    # --- Marca (reutiliza BRAND_* del deploy, con fallback Melilla) ---
    brand_name: str = "Fiscal IA Melilla"
    brand_domain: str = "iamelilla.com"
    # --- SMTP (SiteGround, email del dominio) ---
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "hola@iamelilla.com"
    smtp_from_name: str = "Fiscal IA Melilla"
    smtp_use_ssl: bool = True
    # --- Notificación de leads ---
    owner_notify_email: str = ""  # dónde recibe Joaquín los avisos de lead
    # --- Google Calendar ---
    calendar_token_key: str = ""  # clave Fernet para cifrar el refresh token
    calendar_account_email: str = ""  # email Google de Joaquín (titular agenda)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    # --- Disponibilidad (provisional; override por env tras reunión Joaquín) ---
    timezone: str = "Europe/Madrid"  # Melilla = horario peninsular
    work_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    work_windows: list[tuple[str, str]] = field(
        default_factory=lambda: [("10:00", "14:00"), ("17:00", "20:00")]
    )
    slot_minutes: int = 30
    buffer_minutes: int = 15
    booking_horizon_days: int = 10  # cuántos días hacia delante ofrecer
    # --- Anti-abuso ---
    daily_token_cap_per_ip: int = 50_000
    max_messages_per_conversation: int = 40
    require_magic_link: bool = True  # confirmar email antes de bookear

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def calendar_configured(self) -> bool:
        return bool(self.calendar_token_key and self.calendar_account_email)

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


def _build() -> LeadbotConfig:
    # Marca: hereda BRAND_NAME/BRAND_DOMAIN del deploy si están, con fallback Melilla.
    brand_name = _get("BRAND_NAME") or "Fiscal IA Melilla"
    brand_domain = _get("BRAND_DOMAIN") or "iamelilla.com"
    return LeadbotConfig(
        openai_api_key=_get("OPENAI_API_KEY"),
        model=_get("LEADBOT_MODEL") or "gpt-5-nano",
        reasoning_effort=_get("LEADBOT_REASONING_EFFORT") or "minimal",
        max_completion_tokens=_get_int("LEADBOT_MAX_COMPLETION_TOKENS", 1200),
        brand_name=brand_name,
        brand_domain=brand_domain,
        smtp_host=_get("SMTP_HOST"),
        smtp_port=_get_int("SMTP_PORT", 465),
        smtp_user=_get("SMTP_USER"),
        smtp_password=_get("SMTP_PASSWORD"),
        smtp_from_email=_get("SMTP_FROM_EMAIL") or f"hola@{brand_domain}",
        smtp_from_name=_get("SMTP_FROM_NAME") or brand_name,
        smtp_use_ssl=_get("SMTP_USE_SSL", "true").lower() != "false",
        owner_notify_email=_get("LEADBOT_OWNER_NOTIFY_EMAIL") or _get("SMTP_FROM_EMAIL"),
        calendar_token_key=_get("CALENDAR_TOKEN_KEY"),
        calendar_account_email=_get("LEADBOT_CALENDAR_EMAIL"),
        google_oauth_client_id=_get("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=_get("GOOGLE_OAUTH_CLIENT_SECRET"),
        timezone=_get("LEADBOT_TIMEZONE") or "Europe/Madrid",
        work_days=_parse_days(_get("LEADBOT_WORK_DAYS"), [0, 1, 2, 3, 4]),
        work_windows=_parse_windows(
            _get("LEADBOT_WORK_HOURS"), [("10:00", "14:00"), ("17:00", "20:00")]
        ),
        slot_minutes=_get_int("LEADBOT_SLOT_MINUTES", 30),
        buffer_minutes=_get_int("LEADBOT_BUFFER_MINUTES", 15),
        booking_horizon_days=_get_int("LEADBOT_BOOKING_HORIZON_DAYS", 10),
        daily_token_cap_per_ip=_get_int("LEADBOT_DAILY_TOKEN_CAP_PER_IP", 50_000),
        max_messages_per_conversation=_get_int("LEADBOT_MAX_MESSAGES", 40),
        require_magic_link=_get("LEADBOT_REQUIRE_MAGIC_LINK", "true").lower() != "false",
    )


_config: LeadbotConfig | None = None


def get_leadbot_config() -> LeadbotConfig:
    """Singleton perezoso. ``reload_leadbot_config()`` para tests."""
    global _config
    if _config is None:
        _config = _build()
    return _config


def reload_leadbot_config() -> LeadbotConfig:
    """Reconstruye desde el entorno actual (útil en tests con monkeypatch)."""
    global _config
    _config = _build()
    return _config
