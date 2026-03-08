"""
Tests for the casilla lookup tool and seed script parser.

Covers:
  - .properties file parsing logic (no DB needed)
  - _is_numeric_query / _normalize_casilla_num helpers
  - Tool executor: numeric lookup, text search, empty results, restricted mode
  - Tool registration in __init__
"""
import asyncio
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Make sure 'app' is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# Import parse helpers directly (no DB needed)
# ---------------------------------------------------------------------------

from scripts.seed_casillas import (
    parse_xsd_file,
    parse_dlg_file,
    merge_entries,
    _parse_casilla_num,
    _path_to_section,
)
from app.tools.casilla_lookup_tool import (
    _is_numeric_query,
    _normalize_casilla_num,
    _format_results,
    lookup_casilla_tool,
    CASILLA_LOOKUP_TOOL,
)


# ===========================================================================
# Parser unit tests (no I/O required — uses in-memory data)
# ===========================================================================

class TestParseCasillaNum:
    def test_star_four_digits(self):
        assert _parse_casilla_num("*0505") == "0505"

    def test_star_three_digits(self):
        assert _parse_casilla_num("*505") == "0505"

    def test_star_two_digits(self):
        assert _parse_casilla_num("*01") == "0001"

    def test_star_single_digit(self):
        assert _parse_casilla_num("*1") == "0001"

    def test_hash_returns_none(self):
        assert _parse_casilla_num("###") is None

    def test_range_returns_first(self):
        # '*06-09' -> '0006'
        result = _parse_casilla_num("*06-09")
        assert result == "0006"

    def test_already_padded(self):
        assert _parse_casilla_num("*0020") == "0020"


class TestPathToSection:
    def test_pagina12(self):
        result = _path_to_section("/Declaracion/Pagina12/CuotaIntegra")
        assert "12" in result or "Cuota" in result or "Calculo" in result

    def test_datos_identificativos(self):
        result = _path_to_section("/DatosIdentificativos/Declarante/DPNIF_D")
        assert result  # non-empty

    def test_unknown_path_returns_something(self):
        result = _path_to_section("/UnknownRoot/SomeLeaf")
        assert isinstance(result, str)
        assert len(result) > 0


class TestParseXSDFileMock:
    """Test parser using a temporary in-memory mock file (no actual file required)."""

    def _create_temp_file(self, tmp_path: Path, lines: list[str]) -> Path:
        p = tmp_path / "test.properties"
        p.write_text("\n".join(lines), encoding="iso-8859-1")
        return p

    def test_parse_basic_entry(self, tmp_path):
        lines = [
            "DPNIF_D=[/DatosIdentificativos/Declarante/DPNIF_D][X][*01][Primer Declarante: NIF]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_xsd_file(f, encoding="iso-8859-1")
        assert "0001" in entries
        assert entries["0001"]["description"] == "Primer Declarante: NIF"
        assert entries["0001"]["source"] == "xsd"

    def test_parse_skips_hash(self, tmp_path):
        lines = [
            "INDV=[/DatosIdentificativos/Declarante/INDV][LGC][###][Sin casilla]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_xsd_file(f, encoding="iso-8859-1")
        assert len(entries) == 0

    def test_parse_four_digit_casilla(self, tmp_path):
        lines = [
            "Z1=[/DatosEconomicos/Pagina12/CuotaIntegra][P102][*0505][Cuota integra estatal]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_xsd_file(f, encoding="iso-8859-1")
        assert "0505" in entries
        assert "Cuota integra" in entries["0505"]["description"]

    def test_parse_deduplicates_same_casilla(self, tmp_path):
        lines = [
            "A=[/A/B][X][*01][First description]",
            "C=[/D/E][X][*01][Second description]",  # same casilla, should be ignored
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_xsd_file(f, encoding="iso-8859-1")
        assert len(entries) == 1
        assert entries["0001"]["description"] == "First description"

    def test_parse_nonexistent_file_returns_empty(self, tmp_path):
        entries = parse_xsd_file(tmp_path / "nonexistent.properties")
        assert entries == {}


class TestParseDlgFileMock:
    def _create_temp_file(self, tmp_path: Path, lines: list[str]) -> Path:
        p = tmp_path / "dlg.properties"
        p.write_text("\n".join(lines), encoding="iso-8859-1")
        return p

    def test_parse_dlg_with_context(self, tmp_path):
        lines = [
            "VNUMMDES=[/DatosIdentificativos/Hijos][P010][*75]{Descendientes con discapacidad}[Numero de contribuyentes]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_dlg_file(f, encoding="iso-8859-1")
        assert "0075" in entries
        assert entries["0075"]["description"] == "Numero de contribuyentes"
        assert entries["0075"]["source"] == "dlg"

    def test_parse_dlg_without_context(self, tmp_path):
        lines = [
            "DPNIF_D=[/DatosIdentificativos/Declarante/DPNIF_D][X][*01][NIF del declarante]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_dlg_file(f, encoding="iso-8859-1")
        assert "0001" in entries
        assert entries["0001"]["description"] == "NIF del declarante"

    def test_parse_dlg_skips_hash(self, tmp_path):
        lines = [
            "FOO=[/A/B][LGC][###]{Some context}[Description]",
        ]
        f = self._create_temp_file(tmp_path, lines)
        entries = parse_dlg_file(f, encoding="iso-8859-1")
        assert len(entries) == 0


class TestMergeEntries:
    def test_dlg_wins_on_conflict(self):
        xsd = {"0001": {"casilla_num": "0001", "description": "XSD desc", "source": "xsd"}}
        dlg = {"0001": {"casilla_num": "0001", "description": "DLG desc", "source": "dlg"}}
        merged = merge_entries(xsd, dlg)
        assert len(merged) == 1
        assert merged[0]["description"] == "DLG desc"
        assert merged[0]["source"] == "dlg"

    def test_xsd_only_entries_preserved(self):
        xsd = {"0002": {"casilla_num": "0002", "description": "XSD only", "source": "xsd"}}
        dlg = {"0003": {"casilla_num": "0003", "description": "DLG only", "source": "dlg"}}
        merged = merge_entries(xsd, dlg)
        nums = {r["casilla_num"] for r in merged}
        assert "0002" in nums
        assert "0003" in nums

    def test_empty_inputs(self):
        assert merge_entries({}, {}) == []

    def test_xsd_only(self):
        xsd = {
            "0001": {"casilla_num": "0001", "description": "A", "source": "xsd"},
            "0002": {"casilla_num": "0002", "description": "B", "source": "xsd"},
        }
        merged = merge_entries(xsd, {})
        assert len(merged) == 2


# ===========================================================================
# Tool helper unit tests
# ===========================================================================

class TestIsNumericQuery:
    def test_pure_digits_1_to_4(self):
        assert _is_numeric_query("1") is True
        assert _is_numeric_query("05") is True
        assert _is_numeric_query("505") is True
        assert _is_numeric_query("0505") is True

    def test_longer_than_4_digits_is_false(self):
        assert _is_numeric_query("05050") is False

    def test_text_is_false(self):
        assert _is_numeric_query("cuota integra") is False

    def test_mixed_is_false(self):
        assert _is_numeric_query("0505a") is False

    def test_empty_is_false(self):
        assert _is_numeric_query("") is False


class TestNormalizeCasillaNum:
    def test_pads_to_4_digits(self):
        assert _normalize_casilla_num("1") == "0001"
        assert _normalize_casilla_num("05") == "0005"
        assert _normalize_casilla_num("505") == "0505"

    def test_already_padded_unchanged(self):
        assert _normalize_casilla_num("0505") == "0505"

    def test_strips_whitespace(self):
        assert _normalize_casilla_num("  505  ") == "0505"


class TestFormatResults:
    def test_empty_results(self):
        result = _format_results([], "0505")
        assert "No encontre" in result
        assert "0505" in result

    def test_single_result(self):
        rows = [{"casilla_num": "0505", "description": "Cuota integra estatal", "section": "Cuota integra"}]
        result = _format_results(rows, "0505")
        assert "0505" in result
        assert "Cuota integra estatal" in result

    def test_multiple_results(self):
        rows = [
            {"casilla_num": "0100", "description": "Rendimientos trabajo", "section": "Trabajo"},
            {"casilla_num": "0101", "description": "Reduccion rendimientos", "section": "Trabajo"},
        ]
        result = _format_results(rows, "trabajo")
        assert "0100" in result
        assert "0101" in result


# ===========================================================================
# Tool executor integration tests (mock DB)
# ===========================================================================

def _make_mock_db(rows: list[dict]):
    """Create a mock TursoClient that returns the given rows from execute()."""
    mock_result = MagicMock()
    mock_result.rows = rows

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


@pytest.mark.asyncio
async def test_executor_numeric_exact_hit():
    rows = [{"casilla_num": "0505", "description": "Cuota integra estatal", "section": "Cuota", "source": "xsd"}]
    mock_db = _make_mock_db(rows)

    with patch("app.tools.casilla_lookup_tool._get_db", AsyncMock(return_value=mock_db)):
        result = await lookup_casilla_tool("505")

    assert result["success"] is True
    assert len(result["results"]) == 1
    assert result["results"][0]["casilla_num"] == "0505"
    assert "0505" in result["formatted_response"]


@pytest.mark.asyncio
async def test_executor_numeric_no_exact_falls_back_to_prefix():
    """When exact match returns nothing, the tool does a LIKE prefix search."""
    empty_result = MagicMock()
    empty_result.rows = []

    prefix_rows = [
        {"casilla_num": "0500", "description": "Base imponible general", "section": "Base", "source": "xsd"},
    ]
    prefix_result = MagicMock()
    prefix_result.rows = prefix_rows

    mock_db = AsyncMock()
    # First call: exact -> empty; second call: prefix -> rows
    mock_db.execute = AsyncMock(side_effect=[empty_result, prefix_result])

    with patch("app.tools.casilla_lookup_tool._get_db", AsyncMock(return_value=mock_db)):
        result = await lookup_casilla_tool("500")

    assert result["success"] is True
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_executor_text_search():
    rows = [
        {"casilla_num": "0020", "description": "Reduccion rendimientos netos trabajo", "section": "Trabajo", "source": "xsd"},
    ]
    mock_db = _make_mock_db(rows)

    with patch("app.tools.casilla_lookup_tool._get_db", AsyncMock(return_value=mock_db)):
        result = await lookup_casilla_tool("rendimientos netos trabajo")

    assert result["success"] is True
    assert "0020" in result["formatted_response"]


@pytest.mark.asyncio
async def test_executor_empty_results():
    mock_db = _make_mock_db([])

    with patch("app.tools.casilla_lookup_tool._get_db", AsyncMock(return_value=mock_db)):
        result = await lookup_casilla_tool("concepto inexistente xyz")

    assert result["success"] is True
    assert "No encontre" in result["formatted_response"]


@pytest.mark.asyncio
async def test_executor_restricted_mode():
    result = await lookup_casilla_tool("0505", restricted_mode=True)
    assert result["success"] is False
    assert result["error"] == "restricted"


@pytest.mark.asyncio
async def test_executor_empty_query():
    result = await lookup_casilla_tool("   ")
    assert result["success"] is False
    assert result["error"] == "empty_query"


@pytest.mark.asyncio
async def test_executor_db_error_returns_failure():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    with patch("app.tools.casilla_lookup_tool._get_db", AsyncMock(return_value=mock_db)):
        result = await lookup_casilla_tool("0505")

    assert result["success"] is False
    assert "DB connection failed" in result["error"]


# ===========================================================================
# Tool registration tests
# ===========================================================================

class TestToolRegistration:
    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS
        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "lookup_casilla" in names

    def test_executor_in_tool_executors(self):
        from app.tools import TOOL_EXECUTORS
        assert "lookup_casilla" in TOOL_EXECUTORS
        assert callable(TOOL_EXECUTORS["lookup_casilla"])

    def test_tool_definition_structure(self):
        assert CASILLA_LOOKUP_TOOL["type"] == "function"
        fn = CASILLA_LOOKUP_TOOL["function"]
        assert fn["name"] == "lookup_casilla"
        assert "query" in fn["parameters"]["properties"]
        assert "query" in fn["parameters"]["required"]

    def test_casilla_lookup_tool_in_all(self):
        from app.tools import __all__
        assert "CASILLA_LOOKUP_TOOL" in __all__
        assert "lookup_casilla_tool" in __all__
