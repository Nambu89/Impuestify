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
    # De manual
    "admin' OR '1'='1",
    "1 UNION SELECT password FROM users",
    "x'; DROP TABLE users--",
    "' OR 1=1 --",
    "1; WAITFOR DELAY '0:0:10'",
    "SELECT LOAD_FILE('/etc/passwd')",
    # Evasiones que la PRIMERA version del fallback dejaba pasar (8 de 9).
    # Enumerar ejemplos de manual da cobertura aparente; hay que describir la
    # FORMA del ataque.
    "admin' OR 'x'='x",  # tautologia con otro literal
    "1 UNION ALL SELECT password FROM users",  # ALL intercalado
    "1 UNION/**/SELECT pass",  # comentario como separador
    "x; DELETE FROM users",  # stacked, verbo distinto de DROP
    "x; UPDATE users SET is_admin=1",  # stacked, escalada
    "' OR TRUE --",  # tautologia sin comillas
    "SELECT pg_sleep(10)",  # time-based de PostgreSQL
    "%27%20OR%201%3D1",  # url-encoded
    "1 INTO DUMPFILE '/tmp/x'",  # variante de OUTFILE
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
    "La sociedad UNION IBERICA SL emite la factura",
    "El 100% deducible y el 21% de IVA",
    "Tengo que actualizar o eliminar la factura duplicada",
    "gastos: luz, agua; internet tambien",
    "Deduccion del 60% por residencia en Melilla",
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


@pytest.mark.parametrize("texto", ATAQUES)
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


def test_el_pipeline_rechaza_de_verdad_con_el_regex_degradado(monkeypatch):
    """Prueba de extremo a extremo: la capa 4 tumba la petición sin LLM.

    Los tests de arriba comprueban el veredicto del validador; este comprueba
    que ese veredicto **llega**. Es lo único que demuestra que `risk_level`
    encaja con lo que el pipeline considera bloqueante — con `"medium"` la
    petición pasaría igual que con el fail-open que esto arregla.
    """
    from app.security import security_pipeline as sp_mod

    monkeypatch.setattr(sp_mod.sql_validator, "client", None)
    # Se aíslan las demás capas: aquí se mide la 4, no el pipeline entero.
    pipeline = sp_mod.SecurityPipeline()
    pipeline.enable_prompt_injection = False
    pipeline.enable_pii = False
    pipeline.enable_topic_classifier = False

    resultado = pipeline.check(question="admin' OR '1'='1", user_id="u1")

    assert resultado.is_safe is False
    assert resultado.layer == "sql_injection"
    # El motivo interno nombra la capa y los patrones: nunca debe llegar al
    # usuario (regla del Bug 104).
    assert resultado.rejection_message
    assert "sql" not in resultado.rejection_message.lower()


def test_el_pipeline_deja_pasar_texto_fiscal_sin_llm(monkeypatch):
    """El contrapunto: sin LLM, una consulta normal no se bloquea."""
    from app.security import security_pipeline as sp_mod

    monkeypatch.setattr(sp_mod.sql_validator, "client", None)
    pipeline = sp_mod.SecurityPipeline()
    pipeline.enable_prompt_injection = False
    pipeline.enable_pii = False
    pipeline.enable_topic_classifier = False

    resultado = pipeline.check(question="Cuanto IRPF pago si gano 30000 EUR?", user_id="u1")

    assert resultado.is_safe is True
