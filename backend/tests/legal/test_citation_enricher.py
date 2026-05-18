"""Tests for the CitationEnricher.

Critical regression: invented citations (NOT in registry) must NEVER
produce a bogus link to BOE. They must stay as plain text.
"""

from __future__ import annotations

import pytest

from app.services.legal.citation_enricher import CitationEnricher, get_citation_enricher
from app.services.legal.registry import YamlLegalNormsRegistry


@pytest.fixture(scope="module")
def enricher() -> CitationEnricher:
    return CitationEnricher(YamlLegalNormsRegistry.from_directory())


# ── Law-level citations ──────────────────────────────────────────────────


def test_enricher_links_ley_37_1992_to_boe(enricher):
    text = "Según la Ley 37/1992 los servicios a EEUU..."
    out = enricher.enrich_markdown(text)
    assert "[Ley 37/1992](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740)" in out


def test_enricher_links_ley_35_2006_lirpf(enricher):
    text = "Ley 35/2006 regula el IRPF."
    out = enricher.enrich_markdown(text)
    assert "[Ley 35/2006](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764)" in out


def test_enricher_links_rd_1624_1992_riva(enricher):
    text = "El RD 1624/1992 desarrolla la LIVA."
    out = enricher.enrich_markdown(text)
    assert "[RD 1624/1992](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28925)" in out


def test_enricher_links_real_decreto_form(enricher):
    text = "Según el Real Decreto 439/2007 el cálculo..."
    out = enricher.enrich_markdown(text)
    assert "[Real Decreto 439/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820)" in out


def test_enricher_links_rd_legislativo_form(enricher):
    text = "Real Decreto Legislativo 5/2004 sobre IRNR."
    out = enricher.enrich_markdown(text)
    assert "[Real Decreto Legislativo 5/2004](" in out
    assert "BOE-A-2004-4527" in out


# ── Article-level citations ──────────────────────────────────────────────


def test_enricher_links_art_69_liva(enricher):
    text = "El Art. 69 LIVA regula la localización."
    out = enricher.enrich_markdown(text)
    assert "[Art. 69 LIVA](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740)" in out


def test_enricher_links_art_68_4_lirpf(enricher):
    text = "Según Art. 68.4 LIRPF la deducción es 60%."
    out = enricher.enrich_markdown(text)
    # The article match includes the subarticle "68.4 LIRPF" in the linked text
    assert "BOE-A-2006-20764" in out
    assert "68.4 LIRPF" in out


# ── CRITICAL: invented citations must NOT generate fake links ────────────


def test_enricher_ignores_invented_law(enricher):
    """Hallucinated 'Ley 99/2099' is NOT in `norms.yaml` → must stay
    plain text (no link to a non-existent BOE document)."""
    text = "Según la Ley 99/2099 (inventada) aplica..."
    out = enricher.enrich_markdown(text)
    assert out == text  # unchanged
    assert "https://www.boe.es" not in out


def test_enricher_ignores_invented_rd(enricher):
    text = "El RD 9999/9999 dice..."
    out = enricher.enrich_markdown(text)
    assert out == text


def test_enricher_ignores_unknown_law_sigla(enricher):
    """A sigla not in registry → no link. (Only known siglas are wired.)"""
    text = "Según Art. 5 LFOO la cosa..."
    out = enricher.enrich_markdown(text)
    assert "[" not in out or "LFOO" not in out  # no link generated


# ── Idempotency + protection of existing markup ──────────────────────────


def test_enricher_is_idempotent(enricher):
    text = "Según la Ley 37/1992 aplicamos IVA."
    once = enricher.enrich_markdown(text)
    twice = enricher.enrich_markdown(once)
    assert once == twice


def test_enricher_does_not_touch_existing_links(enricher):
    """If the LLM already emitted a markdown link, leave it alone."""
    text = "Ver [Ley 37/1992](https://www.tributai.es/...) o consulta."
    out = enricher.enrich_markdown(text)
    # The existing link is preserved verbatim.
    assert "https://www.tributai.es/" in out
    # And we don't duplicate the link with a BOE one.
    assert out.count("Ley 37/1992") == 1


def test_enricher_skips_code_blocks(enricher):
    text = """Texto antes Ley 37/1992 aqui.
```python
# Comentario con Ley 37/1992 dentro de codigo
ley = "Ley 37/1992"
```
Texto despues Ley 37/1992 aqui."""
    out = enricher.enrich_markdown(text)
    # El de fuera SÍ se linkea; el de dentro de la fenced NO.
    assert out.count("[Ley 37/1992]") == 2  # antes y despues, NO dentro
    # El bloque de código sigue intacto.
    assert "# Comentario con Ley 37/1992 dentro de codigo" in out
    assert 'ley = "Ley 37/1992"' in out


def test_enricher_handles_multiple_citations(enricher):
    text = "La Ley 37/1992 y la Ley 35/2006 son fundamentales junto al RD 439/2007."
    out = enricher.enrich_markdown(text)
    assert out.count("https://www.boe.es") == 3


def test_enricher_empty_text():
    enr = CitationEnricher(YamlLegalNormsRegistry.from_directory())
    assert enr.enrich_markdown("") == ""
    assert enr.enrich_markdown(None) is None  # type: ignore


# ── Singleton ────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    from app.services.legal.citation_enricher import reset_citation_enricher

    reset_citation_enricher()
    a = get_citation_enricher()
    b = get_citation_enricher()
    assert a is b
    reset_citation_enricher()
