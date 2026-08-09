"""Regresiones de los fixes retropropagados desde `demo/fiscal-ia-melilla`.

Estos arreglos vivieron ~3 meses solo en la rama de la demo IA-Melilla porque
nada en `main` los cubría. Cada test de aquí ancla uno para que no se pierdan
otra vez. Ver `memory/bugfixes-2026-08.md` (bugs 104-108).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.security.pii_detector import PIIDetector
from app.security.rate_limiter import get_rate_limit_key

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Modelo retirado por Google — "Previous models" / shut down, devuelve 404.
RETIRED_GEMINI_MODEL = "gemini-3-flash-preview"


def _groq_saying_safe() -> MagicMock:
    """Cliente Groq mockeado que declara el texto seguro."""
    client = MagicMock()
    message = MagicMock()
    message.content = "safe"
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    client.chat.completions.create.return_value = completion
    return client


def _request(auth_header: str | None = None, ip: str = "203.0.113.7") -> MagicMock:
    request = MagicMock()
    request.headers = {"Authorization": auth_header} if auth_header else {}
    request.client = MagicMock()
    request.client.host = ip
    return request


# ---------------------------------------------------------------------------
# Bug 105 — el detector de PII ignoraba el regex si Groq decía "safe"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "tipo_esperado"),
    [
        ("tengo el DNI 12345678Z, cuanto pago", "DNI español"),
        ("mi correo es fulano@example.com", "Correo electrónico"),
        ("mi IBAN es ES7620770024003102575766", "Cuenta bancaria IBAN"),
    ],
)
def test_regex_gana_cuando_el_llm_es_permisivo(texto: str, tipo_esperado: str):
    """Groq dice "safe" pero el regex encuentra PII de alta confianza → se bloquea.

    El modelo de seguridad es demasiado permisivo en contexto fiscal: un DNI
    dentro de una consulta tributaria "tiene sentido" y lo daba por bueno.
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    result = detector.detect(texto)

    assert result.has_pii is True, f"PII no detectada en: {texto!r}"
    assert tipo_esperado in result.detected_types


@pytest.mark.parametrize(
    "texto",
    [
        "cuanto IRPF pago si gano 30000 EUR en Madrid",
        "he facturado 45000 este ejercicio",
        "el resultado de la casilla 0505 es 12000 euros",
    ],
)
def test_importes_no_se_confunden_con_codigo_postal(texto: str):
    """Un importe de 5 cifras NO es PII.

    El patrón ``postal_code`` matchea cualquier número entre 01000 y 52999, así
    que si se le deja invalidar el veredicto del LLM bloquea prácticamente
    cualquier pregunta fiscal con importes. Queda fuera de
    ``_HIGH_CONFIDENCE_PII`` justo por esto.
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    result = detector.detect(texto)

    assert (
        result.has_pii is False
    ), f"falso positivo: {texto!r} bloqueado como PII {result.detected_types}"


def test_postal_code_sigue_contando_como_fallback_sin_llm():
    """Sin cliente Groq y con input largo, el regex actúa solo y sí lo cuenta.

    Excluir ``postal_code`` del override no debe desactivarlo en la ruta de
    fallback determinista.
    """
    detector = PIIDetector()
    detector.client = None
    texto_largo = "codigo postal 28013 " + ("relleno " * 500)

    result = detector.detect(texto_largo)

    assert "Código Postal" in result.detected_types


# ---------------------------------------------------------------------------
# Bug 107 — rate limit keyeado por token en vez de por usuario
# ---------------------------------------------------------------------------


def _token_for(user_id: str, *, jti: str) -> str:
    from jose import jwt

    return jwt.encode(
        {"sub": user_id, "email": "user@example.com", "jti": jti},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def test_rate_limit_key_estable_entre_tokens_del_mismo_usuario():
    """Volver a hacer login NO debe dar un contador nuevo.

    Antes se keyeaba por ``md5(Authorization)``: cada token nuevo era un bucket
    nuevo, así que cualquiera podía resetear su propio rate limit.
    """
    primero = _token_for("user-42", jti="sesion-1")
    segundo = _token_for("user-42", jti="sesion-2")
    assert primero != segundo, "los dos tokens deben ser distintos"

    key1 = get_rate_limit_key(_request(f"Bearer {primero}"))
    key2 = get_rate_limit_key(_request(f"Bearer {segundo}"))

    assert key1 == key2 == "user:user-42"


def test_rate_limit_key_distingue_usuarios():
    key_a = get_rate_limit_key(_request(f"Bearer {_token_for('user-a', jti='x')}"))
    key_b = get_rate_limit_key(_request(f"Bearer {_token_for('user-b', jti='x')}"))
    assert key_a != key_b


@pytest.mark.parametrize(
    "header",
    [None, "Bearer no-es-un-jwt", "Bearer ", "Basic dXNlcjpwYXNz"],
)
def test_rate_limit_key_cae_a_ip_sin_token_valido(header):
    """Nunca debe lanzar: una excepción aquí hace que slowapi devuelva 500."""
    key = get_rate_limit_key(_request(header, ip="198.51.100.9"))
    assert key == "198.51.100.9"


# ---------------------------------------------------------------------------
# Bug 106 — id de modelo Gemini retirado y hardcodeado
# ---------------------------------------------------------------------------


def test_config_no_apunta_al_modelo_retirado():
    assert settings.GEMINI_MODEL != RETIRED_GEMINI_MODEL


def test_ningun_modulo_hardcodea_un_modelo_gemini():
    """Todo call site debe leer ``settings.GEMINI_MODEL``.

    6 de los 9 call sites tenían el id incrustado, así que cuando Google retiró
    el modelo la env var de Railway no servía de nada. El único literal
    permitido es el default de ``config.py``.
    """
    ofensores: list[str] = []
    for py in APP_DIR.rglob("*.py"):
        if py.name == "config.py":
            continue
        texto = py.read_text(encoding="utf-8", errors="replace")
        for num, linea in enumerate(texto.splitlines(), start=1):
            if "gemini-" not in linea:
                continue
            despojada = linea.strip()
            if despojada.startswith("#") or despojada.startswith("*"):
                continue  # comentario
            if '"gemini-' in linea or "'gemini-" in linea:
                ofensores.append(f"{py.relative_to(APP_DIR.parent)}:{num}: {despojada}")

    assert not ofensores, "id de modelo Gemini hardcodeado:\n" + "\n".join(ofensores)
