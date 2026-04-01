"""
Tests for extended memory extraction patterns in UserMemoryService.

Covers 9 new fiscal fact patterns: hipoteca, guarderia, plan_pensiones,
donaciones, criptomonedas, alquiler, autonomo_gastos, discapacidad, familia_numerosa.
"""
import pytest
from app.services.user_memory_service import UserMemoryService


def _make_service() -> UserMemoryService:
    """Create a UserMemoryService without initializing external deps."""
    svc = UserMemoryService.__new__(UserMemoryService)
    svc.db = None
    svc._vector_index = None
    svc._openai_client = None
    return svc


# === Hipoteca ===

def test_extract_hipoteca():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Pago una hipoteca de 800 euros al mes")
    assert any(f.fact_type == "hipoteca" for f in facts)


def test_extract_hipoteca_prestamo():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Tengo un préstamo hipotecario desde 2018")
    assert any(f.fact_type == "hipoteca" for f in facts)


# === Guarderia ===

def test_extract_guarderia():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Mi hijo va a la guarderia desde septiembre")
    assert any(f.fact_type == "guarderia" for f in facts)


def test_extract_guarderia_escuela_infantil():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Pago la escuela infantil de mi hija")
    assert any(f.fact_type == "guarderia" for f in facts)


# === Plan de pensiones ===

def test_extract_plan_pensiones():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Aporto 2000 euros al plan de pensiones")
    assert any(f.fact_type == "plan_pensiones" for f in facts)


def test_extract_plan_pensiones_aportacion():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Hago aportaciones a mi plan de pensiones cada mes")
    assert any(f.fact_type == "plan_pensiones" for f in facts)


# === Donaciones ===

def test_extract_donaciones():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Hice donativos a una ONG por 500 euros")
    assert any(f.fact_type == "donaciones" for f in facts)


def test_extract_donaciones_fundacion():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Dono a una fundacion cada mes")
    assert any(f.fact_type == "donaciones" for f in facts)


# === Criptomonedas ===

def test_extract_cripto():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Tengo bitcoin en Binance y algo de ethereum")
    assert any(f.fact_type == "criptomonedas" for f in facts)


def test_extract_cripto_generic():
    svc = _make_service()
    facts = svc.extract_facts_from_message("He invertido en criptomonedas este ano")
    assert any(f.fact_type == "criptomonedas" for f in facts)


# === Alquiler ===

def test_extract_alquiler():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Pago un alquiler de 700 euros mensuales")
    assert any(f.fact_type == "alquiler" for f in facts)


def test_extract_alquiler_inquilino():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Soy inquilino en un piso en Barcelona")
    assert any(f.fact_type == "alquiler" for f in facts)


# === Autonomo gastos ===

def test_extract_autonomo_gastos():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Quiero deducir gastos de suministros de mi oficina")
    assert any(f.fact_type == "autonomo_gastos" for f in facts)


def test_extract_autonomo_gastos_coworking():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Pago un coworking cada mes")
    assert any(f.fact_type == "autonomo_gastos" for f in facts)


# === Discapacidad ===

def test_extract_discapacidad():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Tengo un 33% de discapacidad reconocida")
    assert any(f.fact_type == "discapacidad" for f in facts)


def test_extract_discapacidad_minusvalia():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Tengo reconocida una minusvalia del 65%")
    assert any(f.fact_type == "discapacidad" for f in facts)


# === Familia numerosa ===

def test_extract_familia_numerosa():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Somos familia numerosa con 4 hijos")
    assert any(f.fact_type == "familia_numerosa" for f in facts)


def test_extract_familia_numerosa_titulo():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Tenemos titulo de familia numerosa")
    assert any(f.fact_type == "familia_numerosa" for f in facts)


# === False positives ===

def test_no_false_positives_on_generic_text():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Hola, quiero saber sobre la renta")
    extended_types = {
        "hipoteca", "guarderia", "plan_pensiones", "donaciones",
        "criptomonedas", "alquiler", "autonomo_gastos", "discapacidad",
        "familia_numerosa",
    }
    for f in facts:
        assert f.fact_type not in extended_types, f"False positive: {f.fact_type}"


def test_no_false_positives_on_simple_question():
    svc = _make_service()
    facts = svc.extract_facts_from_message("Cual es el plazo para presentar el modelo 100?")
    extended_types = {
        "hipoteca", "guarderia", "plan_pensiones", "donaciones",
        "criptomonedas", "alquiler", "autonomo_gastos", "discapacidad",
        "familia_numerosa",
    }
    for f in facts:
        assert f.fact_type not in extended_types, f"False positive: {f.fact_type}"
