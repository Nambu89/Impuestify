"""Grant OAuth one-time del Google Calendar de Joaquín para el leadbot.

Ejecutar UNA vez, con Joaquín delante, en una máquina con navegador:

    cd backend
    python scripts/leadbot_grant_calendar_oauth.py

Requisitos de entorno (.env raíz):
    GOOGLE_OAUTH_CLIENT_ID      — client id OAuth (tipo "Desktop app" o "Web")
    GOOGLE_OAUTH_CLIENT_SECRET  — client secret
    CALENDAR_TOKEN_KEY          — clave Fernet (genérala con el comando de abajo)
    LEADBOT_CALENDAR_EMAIL      — email de la cuenta Google de Joaquín
    TURSO_DATABASE_URL / TURSO_AUTH_TOKEN

Generar la clave Fernet:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Importante (loopback, NO OOB — deprecado 2023):
- En Google Cloud Console > Credenciales, añade el redirect URI
  ``http://127.0.0.1`` (o usa un client de tipo Desktop, que lo permite).
- La pantalla de consentimiento OAuth debe estar "In production" para que el
  refresh token no caduque a los 7 días (modo testing).

El flujo pide ``access_type=offline`` + ``prompt=consent`` para forzar la
emisión de un refresh token, que se guarda CIFRADO (Fernet) en la tabla
``leadbot_oauth_credentials``.
"""

import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient  # noqa: E402
from app.leadbot.calendar_service import CALENDAR_SCOPES  # noqa: E402
from app.leadbot.config import reload_leadbot_config  # noqa: E402
from app.leadbot.crypto import encrypt_token  # noqa: E402
from app.leadbot.repository import LeadRepository  # noqa: E402
from app.leadbot.schema import ensure_leadbot_schema  # noqa: E402


def run_oauth_flow(client_id: str, client_secret: str) -> str:
    """Lanza el flujo OAuth loopback y devuelve el refresh token (str)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://127.0.0.1"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, CALENDAR_SCOPES)
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Abre esta URL y autoriza con la cuenta de Joaquín:\n{url}",
        success_message="Autorización completada. Vuelve a la terminal.",
    )
    if not creds.refresh_token:
        raise RuntimeError(
            "Google no devolvió refresh_token. Revisa access_type=offline + prompt=consent "
            "y que la app esté 'In production'."
        )
    return creds.refresh_token


async def main() -> None:
    cfg = reload_leadbot_config()
    client_id = cfg.google_oauth_client_id
    client_secret = cfg.google_oauth_client_secret
    account_email = cfg.calendar_account_email

    missing = [
        name
        for name, val in [
            ("GOOGLE_OAUTH_CLIENT_ID", client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", client_secret),
            ("CALENDAR_TOKEN_KEY", cfg.calendar_token_key),
            ("LEADBOT_CALENDAR_EMAIL", account_email),
        ]
        if not val
    ]
    if missing:
        print("❌ Faltan variables de entorno: " + ", ".join(missing))
        sys.exit(1)

    if not (os.environ.get("TURSO_DATABASE_URL") and os.environ.get("TURSO_AUTH_TOKEN")):
        print("❌ Faltan TURSO_DATABASE_URL / TURSO_AUTH_TOKEN")
        sys.exit(1)

    print(f"🔐 Iniciando OAuth para {account_email} …")
    refresh_token = run_oauth_flow(client_id, client_secret)
    print("✅ Refresh token obtenido")

    db = TursoClient()
    await db.connect()
    await ensure_leadbot_schema(db)
    repo = LeadRepository(db)
    await repo.save_oauth_credential(
        account_email=account_email,
        refresh_token_encrypted=encrypt_token(refresh_token),
        scopes=" ".join(CALENDAR_SCOPES),
    )
    await db.disconnect()
    print(f"✅ Credencial guardada (cifrada) para {account_email}. El leadbot ya puede reservar.")


if __name__ == "__main__":
    asyncio.run(main())
