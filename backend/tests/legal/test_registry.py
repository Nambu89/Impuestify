"""Tests for the LegalNormsRegistry — YAML loading + lookup integrity.

These tests also serve as schema-integrity tests for the YAML data.
If a maintainer breaks `norms.yaml`/`articles.yaml`/`invoice_templates.yaml`,
CI fails before deploy.
"""
from datetime import date

import pytest

from app.services.legal.loader import LegalDataError, load_all
from app.services.legal.registry import (
    YamlLegalNormsRegistry,
    get_legal_registry,
    reset_legal_registry,
)


@pytest.fixture(scope="module")
def registry() -> YamlLegalNormsRegistry:
    return YamlLegalNormsRegistry.from_directory()


# ── YAML schema integrity ────────────────────────────────────────────────


def test_yamls_load_without_errors():
    """If any YAML breaks validation this test fails — CI gate."""
    norms, articles, templates = load_all()
    assert len(norms.norms) > 10, "norms.yaml should have all fundamental tax laws"
    assert len(articles.articles) > 20, "articles.yaml should have canonical articles"
    assert len(templates.templates) >= 5, "invoice_templates.yaml should cover main scenarios"


def test_all_articles_reference_existing_norms():
    """Every article.law must match a norm in norms.yaml — referential integrity."""
    norms, articles, _ = load_all()
    valid_siglas = {n.sigla.upper() for n in norms.norms}
    for art in articles.articles:
        assert art.law.upper() in valid_siglas, (
            f"Article {art.article} references unknown law '{art.law}'. "
            f"Add it to norms.yaml or fix the article entry."
        )


def test_all_norms_have_boe_id():
    """Every norm in norms.yaml must carry a `boe_id` matching the official
    BOE-A-NNNN-NNNN format. Required for BOE API integration (sesión 42)."""
    import re
    norms, _, _ = load_all()
    pattern = re.compile(r"^BOE-[A-Z]-\d{4}-\d+$")
    for norm in norms.norms:
        assert norm.boe_id is not None, (
            f"Norm '{norm.sigla}' lacks boe_id — required for BOE API links + vigencia check"
        )
        assert pattern.match(norm.boe_id), (
            f"Norm '{norm.sigla}' has invalid boe_id format: '{norm.boe_id}'"
        )


def test_all_norms_have_url_html_or_can_construct():
    """Every norm should either have `url_html_consolidada` cached OR have
    a `boe_id` so the URL can be reconstructed at request time."""
    norms, _, _ = load_all()
    for norm in norms.norms:
        has_url = norm.url_html_consolidada is not None
        has_id = norm.boe_id is not None
        assert has_url or has_id, (
            f"Norm '{norm.sigla}' has neither url_html_consolidada nor boe_id"
        )


# ── is_known_norm ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "citation",
    [
        "ley 37/1992",
        "Ley 37/1992",
        "LEY 37/1992",
        "liva",
        "LIVA",
        "ley del iva",
    ],
)
def test_is_known_norm_liva_variants(registry, citation):
    assert registry.is_known_norm(citation), f"LIVA should be known via '{citation}'"


@pytest.mark.parametrize(
    "citation",
    [
        "ley 35/2006",       # LIRPF
        "ley 27/2014",       # LIS
        "ley 58/2003",       # LGT
        "ley 22/2009",       # Cesión tributos
        "rd 1624/1992",      # RIVA
        "rd 439/2007",       # RIRPF
        "rd legislativo 5/2004",  # TRLIRNR
    ],
)
def test_is_known_norm_other_fundamental(registry, citation):
    assert registry.is_known_norm(citation)


@pytest.mark.parametrize(
    "citation",
    [
        "ley 99/2099",   # invented year
        "ley 0/2000",
        "rd 9999/9999",
    ],
)
def test_is_known_norm_invented_returns_false(registry, citation):
    assert not registry.is_known_norm(citation)


# ── is_known_article ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "citation",
    [
        "art 21 liva",
        "art 25 liva",
        "art 69 liva",
        "art 70 liva",
        "art 84 liva",
        "art 154 liva",
        "art 68 lirpf",
        "art 95 rirpf",
    ],
)
def test_is_known_article_canonical(registry, citation):
    assert registry.is_known_article(citation), (
        f"Canonical article should be known: {citation}"
    )


@pytest.mark.parametrize(
    "citation",
    [
        "art 69.uno.1 liva",
        "art 69.uno.2 liva",
        "art 69.dos.a liva",
        "art 69.dos.d liva",
        "art 69.dos.l liva",
        "art 84.uno.2 liva",
        "art 68.4 lirpf",
        "art 95.6 rirpf",
    ],
)
def test_is_known_article_with_subarticle(registry, citation):
    assert registry.is_known_article(citation)


def test_compound_citation_69_y_70_liva(registry):
    """'art 69 y 70 liva' should be considered known (both articles canonical)."""
    assert registry.is_known_article("art 69 y 70 liva")


def test_compound_citation_short_form(registry):
    """'70 liva' (compound second half captured by extractor) is known."""
    assert registry.is_known_article("70 liva")


@pytest.mark.parametrize(
    "citation",
    [
        "art 999 liva",       # invented
        "art 999.99 lirpf",   # invented
        "art 500 lgt",
    ],
)
def test_is_known_article_invented_returns_false(registry, citation):
    assert not registry.is_known_article(citation)


# ── Invoice templates ────────────────────────────────────────────────────


def test_all_invoice_templates_loadable(registry):
    templates = registry.all_invoice_templates()
    assert len(templates) >= 5
    keys = {t.key for t in templates}
    # Must cover the most common cases:
    assert "b2b_servicios_no_ue" in keys
    assert "b2c_servicios_intangibles_no_ue" in keys
    assert "exportacion_bienes_no_ue" in keys


def test_invoice_template_lookup_by_key(registry):
    tpl = registry.get_invoice_template("b2b_servicios_no_ue")
    assert tpl is not None
    assert "Art. 69" in tpl.legal_basis
    assert "no sujeta" in tpl.text.lower()


# ── Singleton + fallback ─────────────────────────────────────────────────


def test_get_legal_registry_returns_singleton():
    reset_legal_registry()
    a = get_legal_registry()
    b = get_legal_registry()
    assert a is b


def test_registry_fallback_on_missing_yaml(tmp_path):
    """If YAMLs are missing, the registry returns empty but does not crash."""
    reset_legal_registry()
    reg = get_legal_registry(str(tmp_path))   # empty directory
    assert reg is not None
    # Empty registry → nothing is known
    assert not reg.is_known_norm("ley 37/1992")
    assert not reg.is_known_article("art 21 liva")
    reset_legal_registry()


# ── Vigencia (vigent_from/until) ─────────────────────────────────────────


def test_is_vigent_on_future_norm():
    """A norm with vigent_from in the future should NOT be considered known
    when looked up for today."""
    reg = YamlLegalNormsRegistry.from_directory()
    # Verify LIVA is vigent today
    assert reg.is_known_norm("ley 37/1992", as_of=date(2026, 5, 14))
    # Verify it was NOT vigent in 1990 (predates entry into force)
    assert not reg.is_known_norm("ley 37/1992", as_of=date(1990, 1, 1))
