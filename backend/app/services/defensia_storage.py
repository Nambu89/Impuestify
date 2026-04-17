"""DefensIA Storage Service (T2B-013a).

Cifrado AES-256-GCM de documentos subidos por el usuario en DefensIA, con
compresion zstd previa para reducir el tamano del BLOB en Turso. La clave vive
en la env var ``DEFENSIA_STORAGE_KEY`` (32 bytes hex = 64 caracteres).

Invariantes de seguridad
------------------------
1. **NUNCA** cifrar con una clave dummy. Si la env var falta o esta mal
   formada, el servicio arranca en modo ``_disabled=True`` y cualquier
   llamada a :meth:`cifrar` / :meth:`descifrar` lanza
   :class:`DefensiaStorageUnavailable`. El router DefensIA intercepta esa
   excepcion y devuelve ``HTTP 503`` al cliente, sin romper el resto de la
   aplicacion.
2. **Nunca** romper el arranque de la app por secrets faltantes: solo warning
   en logs. El resto de endpoints siguen operativos.
3. AES-GCM con nonce aleatorio de 12 bytes en cada cifrado (standard). Dos
   cifrados del mismo plaintext producen ciphertexts distintos.
4. zstd nivel 3 (balance entre ratio y CPU) para no penalizar uploads grandes
   (>100 KB). Ver riesgo R-8 del plan parte 2.

Decision de producto Q1 (cerrada): opcion B — base64 + zstd + AES-256-GCM en
BLOB. Ver ``plans/2026-04-13-defensia-implementation-plan-part2.md``.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DefensiaStorageUnavailable(RuntimeError):
    """Storage deshabilitado por falta de ``DEFENSIA_STORAGE_KEY``.

    El router DefensIA la traduce a HTTP 503 sin tumbar la aplicacion.
    """


class DefensiaStorage:
    """Servicio de cifrado/descifrado de documentos DefensIA.

    Uso tipico (cuando la env var esta configurada)::

        storage = DefensiaStorage()
        ciphertext, nonce = storage.cifrar(pdf_bytes)
        # ...guardar en columna BLOB...
        original = storage.descifrar(ciphertext, nonce)

    Si ``DEFENSIA_STORAGE_KEY`` no esta configurada, ``storage.is_enabled`` es
    ``False`` y todas las operaciones lanzan
    :class:`DefensiaStorageUnavailable`.
    """

    def __init__(self, key: Optional[bytes] = None):
        self._disabled = False
        self._aes = None
        self._compressor = None
        self._decompressor = None

        raw_key = self._resolve_key(key)
        if raw_key is None:
            # Copilot review #7: alinear comportamiento con el docstring.
            # Sin clave valida el servicio queda explicitamente deshabilitado.
            self._disabled = True
            return

        # Clave valida — lazy import de libs pesadas para mantener el import
        # modulo barato durante el arranque aunque DefensIA no se use.
        try:
            import zstandard as zstd
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            logger.error(
                "DefensIA storage: dependencias no instaladas (%s). "
                "Anade `cryptography` y `zstandard` a requirements.txt.",
                e,
            )
            self._disabled = True
            return

        self._aes = AESGCM(raw_key)
        self._compressor = zstd.ZstdCompressor(level=3)
        self._decompressor = zstd.ZstdDecompressor()

    @staticmethod
    def _resolve_key(key: Optional[bytes]) -> Optional[bytes]:
        """Resuelve la clave a partir de parametro directo o env var.

        Devuelve ``None`` si no hay clave valida (warning en logs). Nunca
        genera una clave dummy.
        """
        if key is not None:
            if len(key) != 32:
                logger.warning(
                    "DefensIA storage: clave directa debe tener 32 bytes "
                    "(recibidos %d). Servicio deshabilitado.",
                    len(key),
                )
                return None
            return key

        key_hex = os.getenv("DEFENSIA_STORAGE_KEY", "")
        if len(key_hex) != 64:
            logger.warning(
                "DEFENSIA_STORAGE_KEY ausente o mal formado (esperado 64 hex "
                "chars, got %d). Servicio de storage DefensIA deshabilitado "
                "- uploads/downloads devolveran HTTP 503. Resto de la app "
                "sigue operativa.",
                len(key_hex),
            )
            return None

        try:
            return bytes.fromhex(key_hex)
        except ValueError:
            logger.warning(
                "DEFENSIA_STORAGE_KEY no es hex valido. Servicio "
                "deshabilitado."
            )
            return None

    @property
    def is_enabled(self) -> bool:
        """``True`` si el servicio tiene clave valida cargada."""
        return not self._disabled and self._aes is not None

    def _ensure_enabled(self) -> None:
        if not self.is_enabled:
            raise DefensiaStorageUnavailable(
                "DefensIA storage service disabled: "
                "DEFENSIA_STORAGE_KEY not configured"
            )

    def cifrar(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        """Comprime con zstd y cifra con AES-256-GCM.

        Parameters
        ----------
        plaintext:
            Contenido del documento en bytes (PDF, XML, etc.).

        Returns
        -------
        tuple(bytes, bytes)
            ``(ciphertext, nonce)`` — nonce de 12 bytes aleatorio. Ambos
            deben persistirse juntos para descifrar mas tarde.

        Raises
        ------
        DefensiaStorageUnavailable
            Si el servicio esta deshabilitado por falta de clave.
        """
        self._ensure_enabled()
        compressed = self._compressor.compress(plaintext)
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, compressed, None)
        return ct, nonce

    def descifrar(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Descifra con AES-256-GCM y descomprime con zstd.

        Raises
        ------
        DefensiaStorageUnavailable
            Si el servicio esta deshabilitado.
        cryptography.exceptions.InvalidTag
            Si el ciphertext/nonce/clave no coinciden (tampering detectado).
        """
        self._ensure_enabled()
        compressed = self._aes.decrypt(nonce, ciphertext, None)
        return self._decompressor.decompress(compressed)
