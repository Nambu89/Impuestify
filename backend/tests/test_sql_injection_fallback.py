"""El validador de SQLi no puede decir "seguro" sin haber mirado nada.

`validate_user_input()` era 100 % LLM y tenía dos ramas que devolvían
`is_safe=True` sin ejecutar ningún patrón: sin cliente Groq, y ante cualquier
error de API. `security_pipeline` llama a esta función y se fía del resultado —
aquí no hay red de seguridad aguas arriba como sí la tiene el detector de PII—,
así que la capa 4 desaparecía en silencio cuando Groq fallaba.

Ver `memory/bugfixes-2026-08.md` (Bug 116).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.security.sql_injection import SQLInjectionValidator

# Inyecciones que ningún usuario escribe por accidente.
ATAQUES = [
    "admin' OR '1'='1",
    "1 UNION SELECT password FROM users",
    "x'; DROP TABLE users--",
    "' OR 1=1 --",
    "1; WAITFOR DELAY '0:0:10'",
    "SELECT LOAD_FILE('/etc/passwd')",
]

# Castellano fiscal real. Varios contienen cadenas que un patrón SQLi ingenuo
# marcaría (`--`, `/* */`, `CHAR(`, `0x`, la palabra UNION).
LEGITIMO = [
    "El IRPF -- que es progresivo -- sube este ano",
    "La casilla 0505 /* la de rendimientos */ va aqui",
    "CHAR( es una funcion de Excel que uso",
    "El codigo hex 0x1F aparece en el fichero",
    "Cuanto IRPF pago si gano 30000 EUR en Melilla?",
    "Necesito presentar el modelo 303 del 4T",
    "Mi empresa se llama UNION Sociedad Limitada",
]


def _cliente_que_revienta(exc: Exception) -> MagicMock:
    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = exc
    return cliente


@pytest.fixture
def validador_sin_llm() -> SQLInjectionValidator:
    v = SQLInjectionValidator()
    v.client = None
    return v


@pytest.mark.parametrize("texto", ATAQUES)
def test_sin_cliente_groq_el_regex_bloquea_la_inyeccion(validador_sin_llm, texto: str):
    result = validador_sin_llm.validate_user_input(texto)

    assert result.is_safe is False, texto
    # El pipeline solo rechaza con risk_level in ("high", "critical"): un
    # veredicto "medium" pasaría igual que el fail-open que esto arregla.
    assert result.risk_level in ("high", "critical"), texto


@pytest.mark.parametrize("texto", LEGITIMO)
def test_sin_cliente_groq_el_texto_fiscal_pasa(validador_sin_llm, texto: str):
    """El arreglo no puede convertirse en un cazador de falsos positivos."""
    result = validador_sin_llm.validate_user_input(texto)

    assert result.is_safe is True, texto


@pytest.mark.parametrize("texto", ATAQUES[:3])
def test_error_de_api_tambien_degrada_al_regex(texto: str):
    """Un 429 o un timeout es MUCHO más frecuente que una API key ausente.

    Era la rama de fail-open que se dispararía de verdad en producción.
    """
    validador = SQLInjectionValidator()
    validador.client = _cliente_que_revienta(Exception("429 rate limit"))

    result = validador.validate_user_input(texto)

    assert result.is_safe is False, texto
    assert result.risk_level in ("high", "critical"), texto


def test_la_degradacion_deja_rastro_en_violations():
    """Que el LLM se haya caído tiene que ser visible, no silencioso."""
    validador = SQLInjectionValidator()
    validador.client = _cliente_que_revienta(Exception("boom"))

    result = validador.validate_user_input("Cuanto pago si gano 30000 EUR?")

    assert result.is_safe is True
    assert any("API_ERROR" in v for v in result.violations)


def test_los_patrones_ruidosos_no_estan_en_la_lista_bloqueante():
    """Guarda explícita contra reintroducir los cinco que dan falso positivo.

    `--`, `/* */`, `CHAR(`, `HEX(` y los literales hex aparecen en castellano
    fiscal legítimo. Los evalúa el LLM, que ve la frase entera; bloquear por
    ellos rechaza consultas buenas. Misma lección que el Bug 114 con el código
    postal.
    """
    patrones = [p.pattern for p in SQLInjectionValidator._BLOCKING_PATTERNS]

    for ruidoso in (r"(--[^\n]*)", r"(/\*.*?\*/)", r"(\bCHAR\s*\()", r"(0x[0-9a-fA-F]+)"):
        assert ruidoso not in patrones, ruidoso
