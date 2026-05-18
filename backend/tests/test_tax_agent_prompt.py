"""Tests for TaxAgent system prompt and _build_prompt enrichments.

Keyword-based (not snapshot-based) so they survive wording tweaks. They
verify that the new sections added to beat TributAI on the EEUU/IVA case
are present in the prompts the LLM sees.

Regression target: caso "Facturo a un cliente en EEUU. ¿Qué IVA aplico?"
where TributAI gave a more usable answer than Impuestify. The new prompt
sections must be discoverable via stable keywords.
"""

import os
import pytest


# Ensure the agent can build a client even without an OpenAI key during tests.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-used")


@pytest.fixture(scope="module")
def agent():
    from app.agents.tax_agent import TaxAgent

    return TaxAgent()


# ── System prompt sections ───────────────────────────────────────────────────


def test_prompt_contains_answer_first_section(agent):
    """The answer-first pattern for B2B/B2C ambiguity must be in the prompt."""
    prompt = agent._get_system_prompt()
    assert "ANSWER-FIRST" in prompt
    # The heuristic for assuming B2B on EEUU invoices must be discoverable.
    assert "B2B" in prompt
    assert "fuera UE" in prompt or "fuera de UE" in prompt or "fuera de la UE" in prompt


def test_prompt_contains_texto_factura_section(agent):
    """The literal-text-for-invoices block must be in the prompt with
    copy-paste templates for the most common operations."""
    prompt = agent._get_system_prompt()
    assert "TEXTO LITERAL" in prompt
    assert "factura" in prompt.lower()
    # Specific template for EEUU/non-EU B2B (the case that triggered the fix).
    assert "Arts. 69 y 70" in prompt or "Art. 69" in prompt
    assert "Ley 37/1992" in prompt


def test_prompt_contains_pro_tip_section(agent):
    """Pro tip section must be present with REDEME mentioned (the case
    that TributAI used to differentiate)."""
    prompt = agent._get_system_prompt()
    assert "EJEMPLOS Y PRO TIP" in prompt or "Pro tip" in prompt
    assert "REDEME" in prompt


def test_prompt_cites_correct_articles_for_services_no_eu():
    """The prompt must cite Art. 69 LIVA for services to non-EU (not
    Art. 21 — Art. 21 is for goods). Plantillas vienen del registry
    YAML, no hardcoded — buscamos la base legal correcta en el render."""
    from app.agents.tax_agent import TaxAgent
    from app.services.legal import get_legal_registry

    prompt = TaxAgent()._get_system_prompt()
    # The B2B-to-non-EU template must reference Art. 69 LIVA.
    registry = get_legal_registry()
    b2b_tpl = registry.get_invoice_template("b2b_servicios_no_ue")
    assert b2b_tpl is not None, "Template b2b_servicios_no_ue should exist in YAML"
    assert (
        "69" in b2b_tpl.legal_basis
    ), f"B2B template should cite Art. 69, got: {b2b_tpl.legal_basis}"
    assert (
        "21" not in b2b_tpl.legal_basis.split(")")[0]
    ), "B2B services template must NOT cite Art. 21 (that's for goods)"
    # Y la plantilla aparece renderizada en el prompt.
    assert "fuera de la Comunidad" in prompt


# ── _build_prompt proactive hints ────────────────────────────────────────────


def test_build_prompt_injects_ccaa_hint_when_iva_and_no_ccaa(agent):
    """When the user asks about IVA but has no CCAA in profile, the
    prompt must include a hint asking the LLM to offer saving CCAA."""
    query = "Tengo un cliente en Nueva York al que voy a facturar consultoría. ¿Qué IVA le pongo?"
    fiscal_profile = {"situacion_laboral": "autonomo", "ccaa_residencia": ""}
    built = agent._build_prompt(query, fiscal_profile=fiscal_profile)
    assert "guardar la CCAA" in built or "guardar CCAA" in built
    assert "/perfil" in built


def test_build_prompt_no_hint_when_ccaa_present(agent):
    """If CCAA is set in profile, the proactive hint must NOT trigger."""
    query = "Tengo un cliente en Nueva York al que voy a facturar consultoría. ¿Qué IVA le pongo?"
    fiscal_profile = {"situacion_laboral": "autonomo", "ccaa_residencia": "Madrid"}
    built = agent._build_prompt(query, fiscal_profile=fiscal_profile)
    assert "guardar la CCAA" not in built
    assert "guardar CCAA" not in built


def test_build_prompt_creator_hint_when_no_iae(agent):
    """When the user mentions YouTube/Twitch/etc but has no IAE in profile,
    inject a hint about saving IAE 8690."""
    query = "Soy creador en YouTube. ¿Cómo facturo a Google Ireland?"
    fiscal_profile = {
        "situacion_laboral": "autonomo",
        "ccaa_residencia": "Madrid",
        "epigrafe_iae": "",
    }
    built = agent._build_prompt(query, fiscal_profile=fiscal_profile)
    assert "epígrafe IAE" in built or "epigrafe IAE" in built
    assert "8690" in built


def test_build_prompt_isd_hint_when_no_ccaa(agent):
    """ISD questions without CCAA must trigger a hint with ISD bonus mentions."""
    query = "Mis padres me quieren donar 50.000 euros. ¿Cuánto pago de ISD?"
    fiscal_profile = {"ccaa_residencia": ""}
    built = agent._build_prompt(query, fiscal_profile=fiscal_profile)
    assert "ISD" in built
    # The hint must mention that ISD varies between CCAA — a key value proposition.
    assert "varía" in built or "varia" in built or "varían" in built
