"""
Tests for `calculate_modelo_349_tool` (LLM tool wrapper del Modelo 349).

Cubrimos:
- Routing CCAA (Canarias / Ceuta / Melilla -> rechazo).
- Restricted mode (plan particular -> bloqueo).
- Validacion de operaciones (claves invalidas, importes no numericos, NIF vacio).
- Restriccion negativos solo en clave N.
- Periodicidad embebida (mensual / trimestral / anual).
- Cuadre 303 opcional.
- Validacion VIES opcional (mockeada).
- Tool registry: el tool esta registrado en ALL_TOOLS y TOOL_EXECUTORS.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.tools import ALL_TOOLS, TOOL_EXECUTORS
from app.tools.modelo_349_tool import (
    MODELO_349_TOOL,
    calculate_modelo_349_tool,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _basic_op(**overrides):
    base = {
        "nif_operador": "IE9825613N",
        "nombre": "Google Ireland Ltd",
        "clave": "S",
        "importe": 12_000.0,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Tool registry
# --------------------------------------------------------------------------- #


class TestToolRegistry:
    def test_tool_definition_in_ALL_TOOLS(self) -> None:
        assert MODELO_349_TOOL in ALL_TOOLS

    def test_executor_in_TOOL_EXECUTORS(self) -> None:
        assert "calculate_modelo_349" in TOOL_EXECUTORS
        assert TOOL_EXECUTORS["calculate_modelo_349"] is calculate_modelo_349_tool

    def test_tool_function_name_matches(self) -> None:
        assert MODELO_349_TOOL["function"]["name"] == "calculate_modelo_349"


# --------------------------------------------------------------------------- #
# Restricted mode
# --------------------------------------------------------------------------- #


class TestRestrictedMode:
    @pytest.mark.asyncio
    async def test_restricted_returns_block(self, monkeypatch) -> None:
        # Forzar respuesta determinista del bloqueo
        async def _fake_block():
            return "bloqueado"

        # content_restriction.get_autonomo_block_response es sync en el codigo
        from app.security import content_restriction

        monkeypatch.setattr(
            content_restriction,
            "get_autonomo_block_response",
            lambda: "bloqueado por plan",
        )
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            restricted_mode=True,
        )
        assert result["success"] is False
        assert result["error"] == "restricted"
        assert "bloqueado" in result["formatted_response"]


# --------------------------------------------------------------------------- #
# Routing territorial
# --------------------------------------------------------------------------- #


class TestCcaaRouting:
    @pytest.mark.asyncio
    async def test_canarias_rechazado(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            ccaa="Canarias",
        )
        assert result["success"] is False
        assert result["error"] == "ccaa_no_aplicable"
        assert "Canarias" in result["formatted_response"]
        assert "349" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_ceuta_rechazado(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            ccaa="Ceuta",
        )
        assert result["success"] is False
        assert "IPSI" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_melilla_rechazado(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            ccaa="Melilla",
        )
        assert result["success"] is False
        assert "IPSI" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_madrid_acepta(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            ccaa="Madrid",
            year=2026,
            periodo="1T",
        )
        assert result["success"] is True
        assert result["modelo"] == "349"


# --------------------------------------------------------------------------- #
# Validacion de operaciones
# --------------------------------------------------------------------------- #


class TestValidacionOperaciones:
    @pytest.mark.asyncio
    async def test_lista_vacia_devuelve_error(self) -> None:
        result = await calculate_modelo_349_tool(operaciones=[], year=2026)
        assert result["success"] is False
        assert result["error"] == "sin_operaciones_validas"

    @pytest.mark.asyncio
    async def test_clave_invalida_descartada(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(),
                _basic_op(clave="Z"),
            ],
            year=2026,
        )
        # Una valida queda
        assert result["success"] is True
        assert any("clave 'Z'" in e for e in result["errores_parse"])

    @pytest.mark.asyncio
    async def test_negativo_solo_permitido_en_N(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(),  # valido S positivo
                _basic_op(clave="E", importe=-500),
            ],
            year=2026,
        )
        # E con negativo se descarta
        assert result["success"] is True
        assert any("negativo" in e and "clave E" in e for e in result["errores_parse"])

    @pytest.mark.asyncio
    async def test_importe_no_numerico_descartado(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(),
                _basic_op(importe="cien mil"),
            ],
            year=2026,
        )
        assert result["success"] is True
        assert any("no numerico" in e for e in result["errores_parse"])

    @pytest.mark.asyncio
    async def test_nif_vacio_descartado(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(),
                _basic_op(nif_operador=""),
            ],
            year=2026,
        )
        assert any("NIF-IVA vacio" in e for e in result["errores_parse"])


# --------------------------------------------------------------------------- #
# Periodicidad incrustada
# --------------------------------------------------------------------------- #


class TestPeriodicidadEnTool:
    @pytest.mark.asyncio
    async def test_trimestral_default(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(importe=1000)],
            periodo="2T",
            year=2026,
        )
        assert result["success"] is True
        assert result["periodicidad"] == "trimestral"
        assert "20 de julio" in result["plazo"]

    @pytest.mark.asyncio
    async def test_mensual_por_volumen_actual(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(clave="E", importe=80_000)],
            periodo="06",
            year=2026,
        )
        assert result["periodicidad"] == "mensual"
        # Mes 6 -> plazo en mes 7
        assert "07/2026" in result["plazo"]

    @pytest.mark.asyncio
    async def test_mensual_julio_va_a_agosto(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(clave="E", importe=60_000)],
            periodo="07",
            year=2026,
        )
        assert result["periodicidad"] == "mensual"
        assert "agosto" in result["plazo"]

    @pytest.mark.asyncio
    async def test_mensual_por_trimestre_anterior(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(importe=2000)],
            periodo="2T",
            year=2026,
            importes_4_trimestres_anteriores=[3000, 65_000, 8000, 4000],
        )
        assert result["periodicidad"] == "mensual"

    @pytest.mark.asyncio
    async def test_forzar_anual(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(importe=2000)],
            periodo="anual",
            year=2026,
            forzar_anual=True,
        )
        assert result["periodicidad"] == "anual"
        assert "30 de enero de 2027" in result["plazo"]


# --------------------------------------------------------------------------- #
# Cuadre 303
# --------------------------------------------------------------------------- #


class TestCuadre303EnTool:
    @pytest.mark.asyncio
    async def test_cuadre_perfecto(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(clave="E", importe=10_000),
                _basic_op(clave="A", importe=5_000),
            ],
            periodo="1T",
            year=2026,
            casillas_303={
                "casilla_60": 10_000,
                "casilla_36": 5_000,
                "casilla_38": 0,
            },
        )
        assert result["success"] is True
        assert result["cuadre_303"]["cuadre_ok"] is True
        assert result["cuadre_303"]["warnings"] == []

    @pytest.mark.asyncio
    async def test_cuadre_con_diferencia(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(clave="E", importe=10_000)],
            periodo="1T",
            year=2026,
            casillas_303={"casilla_60": 12_000},
        )
        assert result["cuadre_303"]["cuadre_ok"] is False
        assert result["cuadre_303"]["diff_entregas_bienes"] == 2_000
        assert "Cuadre 303" in result["formatted_response"]


# --------------------------------------------------------------------------- #
# Validacion VIES (mock)
# --------------------------------------------------------------------------- #


class TestVIESEnTool:
    @pytest.mark.asyncio
    async def test_vies_no_se_invoca_si_validar_vies_false(self, monkeypatch) -> None:
        called = {"n": 0}

        async def fake_vies(self, nif, **kwargs):
            called["n"] += 1
            return {"valid": True, "source": "vies"}

        from app.utils.calculators import modelo_349 as m349

        monkeypatch.setattr(m349.Modelo349Calculator, "validate_nif_iva_vies", fake_vies)
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            periodo="1T",
            year=2026,
            validar_vies=False,
        )
        assert result["success"] is True
        assert called["n"] == 0

    @pytest.mark.asyncio
    async def test_vies_warning_se_propaga(self, monkeypatch) -> None:
        async def fake_vies(self, nif, **kwargs):
            return {
                "valid": True,
                "vies_unavailable": True,
                "warning": "VIES caido",
                "source": "fail_open",
            }

        from app.utils.calculators import modelo_349 as m349

        monkeypatch.setattr(m349.Modelo349Calculator, "validate_nif_iva_vies", fake_vies)
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            periodo="1T",
            year=2026,
            validar_vies=True,
        )
        assert result["success"] is True
        assert any("VIES no disponible" in w for w in result["vies_warnings"])
        assert "VIES no disponible" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_vies_invalido_se_warning(self, monkeypatch) -> None:
        async def fake_vies(self, nif, **kwargs):
            return {
                "valid": False,
                "vies_unavailable": False,
                "warning": None,
                "error": "no encontrado",
                "source": "vies",
            }

        from app.utils.calculators import modelo_349 as m349

        monkeypatch.setattr(m349.Modelo349Calculator, "validate_nif_iva_vies", fake_vies)
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op()],
            periodo="1T",
            year=2026,
            validar_vies=True,
        )
        assert any("NO valido" in w for w in result["vies_warnings"])


# --------------------------------------------------------------------------- #
# Output structure
# --------------------------------------------------------------------------- #


class TestOutputStructure:
    @pytest.mark.asyncio
    async def test_keys_completos(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[
                _basic_op(clave="E", importe=10_000, nif_operador="DE111111111"),
                _basic_op(clave="S", importe=5_000, nif_operador="IE9825613N"),
            ],
            periodo="1T",
            year=2026,
        )
        for key in (
            "success", "modelo", "periodicidad", "periodicidad_motivo",
            "periodo", "year", "plazo", "resumen", "totales",
            "nif_validations", "formato_invalidos", "vies_warnings",
            "errores_parse", "formatted_response",
        ):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_formatted_response_contiene_secciones(self) -> None:
        result = await calculate_modelo_349_tool(
            operaciones=[_basic_op(clave="E", importe=10_000)],
            periodo="1T",
            year=2026,
        )
        text = result["formatted_response"]
        assert "Modelo 349" in text
        assert "Periodicidad" in text
        assert "Plazo" in text
        assert "Resumen por clave" in text or "Totales" in text
