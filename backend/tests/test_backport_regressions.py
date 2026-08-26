"""Regresiones de los fixes retropropagados desde `demo/fiscal-ia-melilla`.

Estos arreglos vivieron ~3 meses solo en la rama de la demo IA-Melilla porque
nada en `main` los cubría. Cada test de aquí ancla uno para que no se pierdan
otra vez. Ver `memory/bugfixes-2026-08.md` (bugs 104-108).
"""

from __future__ import annotations

import re
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

    Este test nació cuando existía un patrón ``postal_code`` que casaba con
    cualquier número entre 01000 y 52999 y, si se le dejaba invalidar el
    veredicto del LLM, bloqueaba casi cualquier pregunta fiscal con importes.
    Ese patrón acabó eliminándose (ver la nota en ``PII_PATTERNS``), pero el
    test se queda: la garantía que fija —un importe no se rechaza— es de
    producto y debe seguir cumpliéndose venga de donde venga el veredicto.
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    result = detector.detect(texto)

    assert (
        result.has_pii is False
    ), f"falso positivo: {texto!r} bloqueado como PII {result.detected_types}"


def test_el_regex_no_cortocircuita_la_consulta_al_llm():
    """El regex NO debe devolver antes de llamar a Groq.

    Regresión del merge de la rama demo (PR #17): quedaron superpuestas dos
    implementaciones de ``detect()`` — la de la demo, que hacía regex primero y
    ``return`` inmediato ante cualquier match, y la de union con
    ``_HIGH_CONFIDENCE_PII``. Como la primera cortaba antes, la guarda de alta
    confianza se volvió código muerto y "gano 30000 EUR" volvió a bloquearse.

    Afirmar sobre el veredicto no basta: hay que afirmar que **se consultó al
    LLM**. Es lo único que distingue "el regex no encontró nada" de "el regex
    cortocircuitó".
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    detector.detect("cuanto IRPF pago si gano 30000 EUR en Madrid")

    assert detector.client.chat.completions.create.call_count == 1, (
        "no se consultó al modelo de seguridad: hay un cortocircuito del regex "
        "antes de la llamada a Groq (ver bug del merge #17)"
    )


# ---------------------------------------------------------------------------
# Bug 114 — el regex de CP marcaba importes como PII
# ---------------------------------------------------------------------------


def test_ningun_importe_se_marca_como_pii_por_su_forma():
    """Un número de 5 cifras no puede bloquear una consulta, decida quien decida.

    ``postal_code`` se eliminó de ``PII_PATTERNS``: su rango (01000-52999)
    describe igual de bien un código postal que un importe, y en una app fiscal
    los importes son el caso común. Los intentos de salvarlo exigiendo la
    etiqueta se estrellaron con el castellano real ("deuda a c.p. 30000 EUR",
    donde c/p es *corto plazo*).

    Se prueba por la ruta de >3000 chars, que es donde el regex decide SOLO y
    por tanto donde más daño hacía.
    """
    detector = PIIDetector()
    detector.client = None
    relleno = "Detalle de mi actividad economica del ejercicio. " * 70

    for cola in (
        "Gano 30000 EUR al ano.",
        "Mi base imponible fue 45000 euros.",
        "deuda a c.p. 12500 EUR",
        "deuda a corto plazo (C.P.): 30000 EUR",
        "Vivo en el CP 52001",  # incluso etiquetado: ya no es un patrón
    ):
        texto = relleno + cola
        assert len(texto) > 3000, "el caso exige superar el umbral de regex-only"
        result = detector.detect(texto)
        assert result.has_pii is False, cola
        assert "Código Postal" not in result.detected_types, cola


def test_domicilio_completo_se_detecta_en_texto_largo():
    """Un domicilio SIN otro identificador al lado sigue siendo PII.

    Es el hueco que dejaba quitar ``postal_code``: en la ruta de >3000 chars el
    LLM no interviene, así que si ningún patrón reconoce la dirección, pasa como
    segura. ``postal_address`` describe la FORMA de una dirección (código postal
    + población) en vez de un número suelto, que es lo que la hace separable de
    un importe.
    """
    detector = PIIDetector()
    detector.client = None
    relleno = "Escrito de alegaciones. " * 140

    for cola in (
        "D. Juan Garcia, domicilio fiscal: Calle Mayor 1, 28013 Madrid",
        "domicilio: 52001 Melilla",
        "Av. Europa 3, 08011 Barcelona",
    ):
        texto = relleno + cola
        assert len(texto) > 3000
        result = detector.detect(texto)
        assert result.has_pii is True, cola
        assert "Dirección postal" in result.detected_types, cola


def test_el_pii_de_verdad_se_sigue_cazando_en_texto_largo():
    """Contrapunto: quitar `postal_code` no puede desactivar el resto.

    Evita que la simplificación se lea como "el regex ya no mira nada".
    """
    detector = PIIDetector()
    detector.client = None
    relleno = "Detalle de mi actividad economica del ejercicio. " * 70

    for cola, tipo in (
        ("Mi DNI es 12345678Z", "DNI español"),
        ("escribeme a juan@ejemplo.com", "Correo electrónico"),
        ("mi pasaporte es XDA123456", "Número de pasaporte"),
    ):
        result = detector.detect(relleno + cola)
        assert result.has_pii is True, cola
        assert tipo in result.detected_types, cola


# ---------------------------------------------------------------------------
# Sin cliente Groq: el override por alta confianza es la red de seguridad
# ---------------------------------------------------------------------------


def test_sin_cliente_groq_el_regex_sigue_detectando_pii():
    """Sin cliente y con texto CORTO, el PII de alta confianza sigue cazándose.

    Parece un fail-open, y no lo es: ``_detect_uncached`` devuelve has_pii=False
    con el marcador GROQ_CLIENT_MISSING, y entonces ``detect()`` corre el regex
    y deja mandar a ``_HIGH_CONFIDENCE_PII``. Este test fija ese contrato para
    que a nadie le tiente "arreglarlo" degradando a ``_regex_only`` desde la
    rama sin cliente: eso haría contar TODOS los patrones y convertiría los
    ambiguos en bloqueantes (ver el test siguiente).

    Ojo con la longitud: por encima de 3000 chars ``detect()`` sale por la ruta
    regex-only y nunca llega a la rama ``if not self.client``. Estos textos son
    deliberadamente cortos para ejercitar ESA rama.
    """
    detector = PIIDetector()
    detector.client = None

    for texto, tipo in (
        ("mi DNI es 12345678Z", "DNI español"),
        ("escribeme a juan@ejemplo.com", "Correo electrónico"),
        ("mi telefono es 612345678", "Teléfono español"),
    ):
        assert len(texto) < 3000
        result = detector.detect(texto)
        assert result.has_pii is True, texto
        assert tipo in result.detected_types, texto


def test_expediente_no_se_confunde_con_pasaporte():
    """Un código de expediente es texto legítimo y NO debe rechazarse.

    Comportamiento, no patrón: con el LLM diciendo "safe", el veredicto final
    depende de si ``passport`` invalida ese veredicto. Como está en
    ``_HIGH_CONFIDENCE_PII``, un patrón laxo aquí bloquearía de verdad — por eso
    se comprueba vía ``detect()`` y no con ``re.findall``.

    Los textos con "pasaporte" delante llevan referencias DENTRO de la ventana
    del conector, que es donde estaba el fallo: con 12 caracteres
    "Pasaporte: s/d; exp ABC123456" capturaba la referencia.
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    for texto in (
        "mi expediente es ABC123456",
        "Referencia REC1234567 del TEAR",
        "liquidacion XYZ987654",
        "Pasaporte: s/d; exp ABC123456",
        "pasaporte caducado; ref ABC123456",
    ):
        detector._cache_clear()
        result = detector.detect(texto)
        assert result.has_pii is False, texto
        assert "Número de pasaporte" not in result.detected_types, texto


def test_pasaporte_etiquetado_invalida_el_veredicto_del_llm():
    """Contrapunto: un pasaporte de verdad se rechaza aunque el LLM lo apruebe.

    Es lo que significa estar en ``_HIGH_CONFIDENCE_PII``. Si alguien saca
    ``passport`` de ese conjunto, este test cae.
    """
    detector = PIIDetector()
    detector.client = _groq_saying_safe()

    for texto in ("mi pasaporte es XDA123456", "Pasaporte: AB1234567"):
        detector._cache_clear()
        result = detector.detect(texto)
        assert result.has_pii is True, texto
        assert "Número de pasaporte" in result.detected_types, texto


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
