"""Tests for the citation verifier (Sprint 1 P0 #4)."""

import pytest

from app.security.citation_verifier import (
    Citation,
    extract_citations,
    verify_citations,
    _normalize,
)


# ── Extraction ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected_label",
    [
        ("Art. 68.4 LIRPF", "art_law"),
        ("artículo 105 LGT", "art_law"),
        ("art 27 LIVA", "art_law"),
        ("Art. 31 bis LIS", "art_law"),
        ("Ley 35/2006", "ley"),
        ("Ley 22/2009", "ley"),
        ("RD 439/2007", "rd"),
        ("RD-Ley 13/2022", "rd"),
        ("Real Decreto Legislativo 5/2004", "real_decreto"),
        ("Norma Foral 13/2013", "norma_foral"),
        ("NF 6/2006", "norma_foral"),
        ("Decreto Foral 47/2014", "decreto_foral"),
        ("DF 8/2010", "decreto_foral"),
        ("V0773-22", "consulta_dgt"),
        ("V1234-25", "consulta_dgt"),
        ("BOE núm. 285", "boe"),
    ],
)
def test_extract_single_citation(text, expected_label):
    cites = extract_citations(text)
    assert cites, f"No citation extracted from {text!r}"
    assert any(c.label == expected_label for c in cites), (
        f"Expected label {expected_label} for {text!r}, got {[c.label for c in cites]}"
    )


def test_extract_multiple_unique():
    text = "Según Art. 68.4 LIRPF y la Ley 22/2009, además del RD 439/2007, NF 13/2013 y consulta V0773-22."
    cites = extract_citations(text)
    labels = sorted({c.label for c in cites})
    assert labels == ["art_law", "consulta_dgt", "ley", "norma_foral", "rd"]


def test_extract_empty():
    assert extract_citations("") == []
    assert extract_citations("Sin citas legales.") == []


def test_extract_dedupes_same_normalized():
    text = "Art. 68.4 LIRPF y Artículo 68.4 LIRPF dicen lo mismo."
    cites = extract_citations(text)
    # Both should normalize identically — only one Citation object kept.
    art_law_cites = [c for c in cites if c.label == "art_law"]
    assert len(art_law_cites) == 1


# ── Normalization ────────────────────────────────────────────────────────────


def test_normalize_article_variants():
    assert _normalize("Art. 68") == _normalize("Artículo 68") == _normalize("art 68") == "art 68"


def test_normalize_strips_accents():
    assert "ñ" not in _normalize("año")
    assert "á" not in _normalize("artículo")


# ── Verification ─────────────────────────────────────────────────────────────


def test_verify_all_present():
    response = "Según Art. 68.4 LIRPF y Ley 22/2009 se aplica deducción del 60%."
    chunks = [
        {"id": "c1", "text": "El artículo 68.4 LIRPF regula la deducción por residencia en Ceuta y Melilla"},
        {"id": "c2", "text": "La Ley 22/2009 cede tributos a las CCAA"},
    ]
    result = verify_citations(response, chunks)
    assert not result.has_unverified
    assert all(c.verified for c in result.citations)
    assert result.warning_footer is None


def test_verify_one_missing_flagged():
    response = "Según Art. 99.99 LIRPF (inventado) y Ley 22/2009 (real)."
    chunks = [
        {"id": "c1", "text": "Ley 22/2009 cede tributos a las CCAA"},
    ]
    result = verify_citations(response, chunks)
    assert result.has_unverified
    assert len(result.unverified) == 1
    assert result.unverified[0].text.lower().startswith("art")
    assert result.warning_footer is not None
    assert "no he podido verificar" in result.warning_footer.lower()


def test_verify_empty_chunks_flags_everything():
    response = "Según Art. 68.4 LIRPF y Ley 22/2009 se aplica."
    result = verify_citations(response, rag_chunks=[])
    assert result.has_unverified
    assert len(result.unverified) == len(result.citations)


def test_verify_no_citations_returns_clean():
    result = verify_citations("Hola, qué tal?", rag_chunks=[{"id": "c1", "text": "anything"}])
    assert not result.has_unverified
    assert result.warning_footer is None
    assert result.annotated_response is None


def test_annotated_response_appends_footer():
    response = "Según Art. 99.99 LIRPF (inventado)."
    chunks: list = []
    result = verify_citations(response, chunks)
    assert result.annotated_response is not None
    assert response in result.annotated_response  # original body preserved
    assert "no he podido verificar" in result.annotated_response.lower()


def test_chunks_with_alternative_field_names():
    response = "Según Art. 68.4 LIRPF."
    chunks = [{"chunk_id": "c1", "content": "art 68.4 lirpf — deducción"}]
    result = verify_citations(response, chunks)
    assert all(c.verified for c in result.citations)


def test_consulta_dgt_match():
    response = "Ver consulta V0773-22."
    chunks = [{"id": "c1", "text": "DGT V0773-22 aclara IAE 8690 para creadores de contenido"}]
    result = verify_citations(response, chunks)
    assert all(c.verified for c in result.citations)


def test_no_partial_citation_collision():
    # "Ley 22/2009" should NOT match against a chunk that only has "22/2009" without "Ley".
    response = "Según Ley 22/2009 se aplica."
    chunks = [{"id": "c1", "text": "El año 22/2009 fue importante"}]
    result = verify_citations(response, chunks)
    assert result.has_unverified
