"""Cifrado simétrico del refresh token de Google Calendar (Fernet).

El refresh token de Joaquín es una credencial de larga duración: se guarda
cifrado en reposo (tabla ``leadbot_oauth_credentials``) con una clave Fernet en
la variable de entorno ``CALENDAR_TOKEN_KEY``. Generar la clave una vez con:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import logging

from app.leadbot.config import get_leadbot_config

logger = logging.getLogger(__name__)


def _fernet():
    from cryptography.fernet import Fernet

    key = get_leadbot_config().calendar_token_key
    if not key:
        raise RuntimeError(
            "CALENDAR_TOKEN_KEY no configurada — no se puede cifrar/descifrar "
            "el refresh token de Calendar."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    """Cifra un secreto. Devuelve texto base64 url-safe (str)."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Descifra. Lanza ``cryptography.fernet.InvalidToken`` si la clave no casa."""
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
