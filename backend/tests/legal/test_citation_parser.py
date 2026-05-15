"""Tests for the citation parser."""
import pytest

from app.services.legal.citation_parser import (
    parse_article_citation,
    parse_norm_citation,
    split_compound_article_citation,
)


# ── parse_article_citation ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "input_str,expected_law,expected_article,expected_sub",
    [
        ("art 21 liva", "LIVA", "21", None),
        ("art 69 liva", "LIVA", "69", None),
        ("art 69.uno.1 liva", "LIVA", "69", "Uno.1"),
        ("art 69.dos.d liva", "LIVA", "69", "Dos.d"),
        ("art 84.uno.2 liva", "LIVA", "84", "Uno.2"),
        ("art 68.4 lirpf", "LIRPF", "68", "4"),
        ("art 95.6 rirpf", "RIRPF", "95", "6"),
        ("70 liva", "LIVA", "70", None),
        ("art 31 bis lis", "LIS", "31 bis", None),
    ],
)
def test_parse_article_citation_valid(input_str, expected_law, expected_article, expected_sub):
    parsed = parse_article_citation(input_str)
    assert parsed is not None, f"Failed to parse: {input_str}"
    assert parsed.law == expected_law
    assert parsed.article == expected_article
    assert parsed.subarticle == expected_sub


@pytest.mark.parametrize(
    "input_str",
    [
        "",
        "ley 37/1992",
        "rd 1624/1992",
        "art noventa liva",
        "art lirpf",
    ],
)
def test_parse_article_citation_invalid(input_str):
    assert parse_article_citation(input_str) is None


# ── parse_norm_citation ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "input_str,expected_type,expected_number,expected_year",
    [
        ("ley 37/1992", "ley", 37, 1992),
        ("ley 35/2006", "ley", 35, 2006),
        ("ley 22/2009", "ley", 22, 2009),
        ("rd 1624/1992", "rd", 1624, 1992),
        ("rd-ley 13/2022", "rd", 13, 2022),
        ("real decreto legislativo 5/2004", "rd_legislativo", 5, 2004),
        ("rd legislativo 1/1993", "rd_legislativo", 1, 1993),
        ("norma foral 13/2013", "norma_foral", 13, 2013),
        ("nf 6/2006", "norma_foral", 6, 2006),
        ("decreto foral 47/2014", "decreto_foral", 47, 2014),
    ],
)
def test_parse_norm_citation_valid(input_str, expected_type, expected_number, expected_year):
    parsed = parse_norm_citation(input_str)
    assert parsed is not None, f"Failed to parse: {input_str}"
    assert parsed.norm_type == expected_type
    assert parsed.number == expected_number
    assert parsed.year == expected_year


@pytest.mark.parametrize(
    "input_str",
    [
        "art 21 liva",
        "70 liva",
        "lirpf",
        "constitucion espanola",
    ],
)
def test_parse_norm_citation_invalid(input_str):
    assert parse_norm_citation(input_str) is None


# ── split_compound_article_citation ──────────────────────────────────────


def test_split_compound_y_separator():
    """'art 69 y 70 liva' → two parsed articles."""
    parts = split_compound_article_citation("art 69 y 70 liva")
    assert len(parts) == 2
    assert parts[0].article == "69"
    assert parts[0].law == "LIVA"
    assert parts[1].article == "70"
    assert parts[1].law == "LIVA"


def test_split_compound_single_returns_single():
    parts = split_compound_article_citation("art 21 liva")
    assert len(parts) == 1
    assert parts[0].article == "21"


def test_split_compound_unparseable_returns_empty():
    parts = split_compound_article_citation("foo bar baz")
    assert parts == ()
