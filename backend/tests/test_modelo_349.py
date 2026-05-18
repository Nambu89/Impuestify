"""
Tests for Modelo 349 calculator (Modelo349Calculator).

Cubrimos:
- Validacion de claves (E,A,T,S,I,M,H,R,D,C,N).
- Validacion sintactica de NIF-IVA por pais.
- Mock de VIES (httpx) — fail-open + fail-closed + cache LRU.
- Deteccion de periodicidad (mensual / trimestral / anual) por umbral 50K / 35K-15K.
- Plazos de presentacion (incluyendo julio -> agosto, diciembre -> enero).
- Cuadre 303 <-> 349.
- Resumen agregado por clave (totales y operadores unicos).

VIES integration test real: marcado @pytest.mark.integration y skip por defecto.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.calculators.modelo_349 import (
    CLAVES_VALIDAS,
    CUADRE_TOLERANCIA_EUR,
    UMBRAL_ANUAL_ENTREGAS,
    UMBRAL_ANUAL_TOTAL,
    UMBRAL_MENSUAL_TRIMESTRE,
    Modelo349Calculator,
    Operacion349,
)


# --------------------------------------------------------------------------- #
# Factory helpers
# --------------------------------------------------------------------------- #


def op(
    clave: str, importe: float, nif: str = "IE9825613N", nombre: str = "Acme EU"
) -> Operacion349:
    return Operacion349(nif_operador=nif, nombre=nombre, clave=clave, importe=importe)


# --------------------------------------------------------------------------- #
# Validacion de claves
# --------------------------------------------------------------------------- #


class TestValidateClave:
    @pytest.mark.parametrize("clave", list(CLAVES_VALIDAS))
    def test_each_valid_clave(self, clave: str) -> None:
        assert Modelo349Calculator.validate_clave(clave) is True

    def test_invalid_clave(self) -> None:
        assert Modelo349Calculator.validate_clave("Z") is False
        assert Modelo349Calculator.validate_clave("") is False
        assert Modelo349Calculator.validate_clave("EE") is False

    def test_clave_lowercase_accepted(self) -> None:
        assert Modelo349Calculator.validate_clave("e") is True
        assert Modelo349Calculator.validate_clave("a") is True


# --------------------------------------------------------------------------- #
# Validacion sintactica del NIF-IVA
# --------------------------------------------------------------------------- #


class TestNifIvaFormat:
    def test_normalize_strips_separators(self) -> None:
        assert Modelo349Calculator.normalize_nif_iva(" ie 9825 613-N ") == "IE9825613N"

    def test_ireland_valid(self) -> None:
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("IE9825613N")
        assert ok is True
        assert country == "IE"
        assert motivo is None

    def test_germany_valid(self) -> None:
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("DE123456789")
        assert ok is True
        assert country == "DE"

    def test_germany_too_short(self) -> None:
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("DE12345")
        assert ok is False
        assert country == "DE"
        assert "DE" in motivo

    def test_unknown_country(self) -> None:
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("US123456789")
        assert ok is False
        assert country == "US"
        assert "no es UE" in motivo

    def test_uk_post_brexit_rejected(self) -> None:
        # GB ya no es EU desde 01/01/2021 (Brexit)
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("GB123456789")
        assert ok is False
        assert country == "GB"

    def test_north_ireland_xi_accepted(self) -> None:
        # Irlanda del Norte (XI) sigue en UE para bienes
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("XI123456789")
        assert ok is True
        assert country == "XI"

    def test_too_short_overall(self) -> None:
        ok, country, motivo = Modelo349Calculator.validate_nif_iva_format("DE")
        assert ok is False


# --------------------------------------------------------------------------- #
# VIES — mocked
# --------------------------------------------------------------------------- #


class TestViesMocked:
    @pytest.mark.asyncio
    async def test_vies_valid_response(self) -> None:
        calc = Modelo349Calculator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "name": "GOOGLE IRELAND LIMITED",
            "address": "Gordon House, Dublin 4",
        }
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await calc.validate_nif_iva_vies("IE9825613N", client=mock_client)
        assert result["valid"] is True
        assert result["nombre"] == "GOOGLE IRELAND LIMITED"
        assert result["source"] == "vies"
        assert result["vies_unavailable"] is False

    @pytest.mark.asyncio
    async def test_vies_invalid_format_short_circuits(self) -> None:
        calc = Modelo349Calculator()
        mock_client = MagicMock()
        mock_client.post = AsyncMock()  # no debe llamarse
        result = await calc.validate_nif_iva_vies("ZZ123", client=mock_client)
        assert result["valid"] is False
        assert result["source"] == "format"
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_vies_fail_open_on_500(self) -> None:
        calc = Modelo349Calculator()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await calc.validate_nif_iva_vies("IE9825613N", client=mock_client, fail_open=True)
        assert result["valid"] is True
        assert result["vies_unavailable"] is True
        assert result["source"] == "fail_open"
        assert "500" in result["warning"]

    @pytest.mark.asyncio
    async def test_vies_fail_closed_on_500(self) -> None:
        calc = Modelo349Calculator()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await calc.validate_nif_iva_vies("IE9825613N", client=mock_client, fail_open=False)
        assert result["valid"] is False
        assert "503" in (result["error"] or "")

    @pytest.mark.asyncio
    async def test_vies_cache_hit_avoids_second_call(self) -> None:
        calc = Modelo349Calculator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True, "name": "X", "address": "Y"}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        await calc.validate_nif_iva_vies("IE9825613N", client=mock_client)
        result2 = await calc.validate_nif_iva_vies("IE9825613N", client=mock_client)

        # La segunda llamada debe servirse del cache
        assert result2["source"] == "cache"
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_vies_timeout_fail_open(self) -> None:
        calc = Modelo349Calculator()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=TimeoutError("simulated"))
        mock_client.aclose = AsyncMock()

        result = await calc.validate_nif_iva_vies("DE123456789", client=mock_client, fail_open=True)
        assert result["valid"] is True
        assert result["vies_unavailable"] is True
        assert result["source"] == "fail_open"


# --------------------------------------------------------------------------- #
# Periodicidad
# --------------------------------------------------------------------------- #


class TestPeriodicidad:
    def test_trimestral_por_defecto(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("S", 1000), op("S", 5000)],
            importes_4_trimestres_anteriores=[1000, 2000, 3000, 4000],
        )
        assert info["periodicidad"] == "trimestral"
        assert info["volumen_actual"] == 6000.0

    def test_mensual_por_trimestre_actual(self) -> None:
        # 60.000 EUR en el trimestre actual -> mensual
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("E", 60_000)],
            importes_4_trimestres_anteriores=[],
        )
        assert info["periodicidad"] == "mensual"
        assert info["volumen_actual"] == 60_000.0
        assert "trimestre actual" in info["motivo"]

    def test_mensual_por_trimestre_anterior(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("S", 1000)],
            importes_4_trimestres_anteriores=[5000, 70_000, 1000, 2000],
        )
        assert info["periodicidad"] == "mensual"
        assert info["volumen_anterior_max"] == 70_000

    def test_borde_50k_no_supera(self) -> None:
        # Exactamente 50.000 NO supera (estricto >)
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("E", UMBRAL_MENSUAL_TRIMESTRE)],
            importes_4_trimestres_anteriores=[],
        )
        assert info["periodicidad"] == "trimestral"

    def test_anual_si_volumen_y_entregas_bajo_umbral(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("S", 1000)],
            importes_4_trimestres_anteriores=[],
            operaciones_anuales=[op("S", 10_000), op("A", 5_000)],
        )
        assert info["periodicidad"] == "anual"

    def test_anual_falla_si_entregas_superan_15k(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("S", 1000)],
            importes_4_trimestres_anteriores=[],
            operaciones_anuales=[op("E", 16_000), op("A", 5_000)],
        )
        # Volumen anual 21K (<35K) pero entregas 16K (>15K) -> NO anual, queda trimestral
        assert info["periodicidad"] == "trimestral"

    def test_anual_falla_si_total_supera_35k(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("S", 1000)],
            importes_4_trimestres_anteriores=[],
            operaciones_anuales=[op("E", 10_000), op("A", 30_000)],
        )
        # Total 40K > 35K -> NO anual, queda trimestral
        assert info["periodicidad"] == "trimestral"

    def test_consignacion_no_cuenta_para_umbral(self) -> None:
        # 60.000 en clave R (consignacion) NO debe disparar mensual
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("R", 60_000)],
            importes_4_trimestres_anteriores=[],
        )
        assert info["periodicidad"] == "trimestral"

    def test_rectificacion_n_no_cuenta_para_umbral(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("N", 80_000)],
            importes_4_trimestres_anteriores=[],
        )
        assert info["periodicidad"] == "trimestral"

    def test_forzar_anual(self) -> None:
        info = Modelo349Calculator.detect_periodicidad(
            operaciones_actual=[op("E", 999_999)],
            forzar_anual=True,
        )
        assert info["periodicidad"] == "anual"


# --------------------------------------------------------------------------- #
# Plazos
# --------------------------------------------------------------------------- #


class TestPlazos:
    def test_trimestral_1T(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("trimestral", "1T", 2026)
        assert "20 de abril de 2026" in plazo

    def test_trimestral_4T_va_a_enero_siguiente(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("trimestral", "4T", 2026)
        assert "30 de enero de 2027" in plazo

    def test_mensual_julio_va_a_agosto(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("mensual", "07", 2026)
        assert "agosto" in plazo

    def test_mensual_diciembre_va_a_enero_siguiente(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("mensual", "12", 2026)
        assert "enero de 2027" in plazo

    def test_mensual_normal(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("mensual", "03", 2026)
        assert "04/2026" in plazo

    def test_anual(self) -> None:
        plazo = Modelo349Calculator.plazo_presentacion("anual", "anual", 2026)
        assert "30 de enero de 2027" in plazo


# --------------------------------------------------------------------------- #
# Resumen
# --------------------------------------------------------------------------- #


class TestBuildResumen:
    def test_agrega_por_clave(self) -> None:
        ops = [
            op("E", 10_000, nif="DE111111111"),
            op("E", 5_000, nif="DE111111111"),
            op("E", 2_000, nif="FR12345678901"),
            op("A", 3_000, nif="IT12345678901"),
            op("S", 7_500, nif="IE9825613N"),
            op("N", -200, nif="DE111111111"),
        ]
        resumen = Modelo349Calculator.build_resumen(ops)
        assert resumen["por_clave"]["E"]["importe"] == 17_000
        assert resumen["por_clave"]["E"]["n_operaciones"] == 3
        assert resumen["por_clave"]["E"]["n_operadores"] == 2  # DE + FR
        assert resumen["por_clave"]["A"]["importe"] == 3_000
        assert resumen["por_clave"]["S"]["importe"] == 7_500
        assert resumen["por_clave"]["N"]["importe"] == -200
        assert resumen["operaciones_count"] == 6
        # Operadores unicos: DE, FR, IT, IE = 4
        assert resumen["operadores_unicos"] == 4

    def test_totales_agregados(self) -> None:
        ops = [
            op("E", 1000),
            op("T", 500),
            op("M", 200),
            op("H", 100),  # entregas bienes = 1800
            op("A", 800),  # adquis bienes = 800
            op("S", 600),  # serv prestados = 600
            op("I", 400),  # serv adquiridos = 400
            op("R", 1200),
            op("D", 300),
            op("C", 100),  # consignacion = 1600
            op("N", -50),  # rectif = -50
        ]
        resumen = Modelo349Calculator.build_resumen(ops)
        t = resumen["totales"]
        assert t["entregas_bienes"] == 1800
        assert t["adquisiciones_bienes"] == 800
        assert t["servicios_prestados"] == 600
        assert t["servicios_adquiridos"] == 400
        assert t["consignacion"] == 1600
        assert t["rectificaciones"] == -50
        # volumen relevante = entregas bienes + adq bienes + serv prest + serv adq
        assert t["volumen_relevante"] == 3600
        # total general suma todo (incluye consignacion + rectif)
        assert t["total_general"] == 5150

    def test_clave_invalida_va_a_errores(self) -> None:
        # Construimos una Operacion con clave invalida (warning emitido en post_init pero no rechazada)
        bad = Operacion349(nif_operador="DE111111111", nombre="X", clave="Z", importe=100)
        resumen = Modelo349Calculator.build_resumen([bad])
        assert any("Z" in e for e in resumen["errores"])
        assert resumen["operaciones_count"] == 1


# --------------------------------------------------------------------------- #
# Cuadre 303 <-> 349
# --------------------------------------------------------------------------- #


class TestCuadre303:
    def test_cuadre_perfecto(self) -> None:
        ops = [op("E", 10_000), op("A", 5_000)]
        cuadre = Modelo349Calculator.cuadrar_con_303(
            operaciones_349=ops,
            casillas_303={"casilla_60": 10_000, "casilla_36": 5_000, "casilla_38": 0},
        )
        assert cuadre.cuadre_ok is True
        assert cuadre.diff_entregas_bienes == 0
        assert cuadre.diff_adquisiciones_bienes == 0
        assert cuadre.warnings == []

    def test_cuadre_dentro_tolerancia(self) -> None:
        ops = [op("E", 10_000.0), op("A", 5_000.0)]
        cuadre = Modelo349Calculator.cuadrar_con_303(
            operaciones_349=ops,
            casillas_303={"casilla_60": 10_000.30, "casilla_36": 5_000.20, "casilla_38": 0},
        )
        # Dentro de 0,5 EUR -> OK
        assert cuadre.cuadre_ok is True

    def test_cuadre_diferencia_bienes_genera_warning(self) -> None:
        ops = [op("E", 10_000)]
        cuadre = Modelo349Calculator.cuadrar_con_303(
            operaciones_349=ops,
            casillas_303={"casilla_60": 12_000},
        )
        assert cuadre.cuadre_ok is False
        assert cuadre.diff_entregas_bienes == 2_000
        assert any("EIB" in w for w in cuadre.warnings)

    def test_cuadre_diferencia_adquisiciones(self) -> None:
        ops = [op("A", 5_000)]
        cuadre = Modelo349Calculator.cuadrar_con_303(
            operaciones_349=ops,
            casillas_303={"casilla_36": 4_000, "casilla_38": 500},
        )
        assert cuadre.cuadre_ok is False
        # 303: 4000 + 500 = 4500 vs 349: 5000 -> diff = -500
        assert cuadre.diff_adquisiciones_bienes == -500
        assert any("AIB" in w for w in cuadre.warnings)

    def test_cuadre_servicios_son_informativos(self) -> None:
        # Servicios S/I no tienen casilla 303 directa, no rompen el cuadre
        ops = [op("S", 7_500), op("I", 3_000)]
        cuadre = Modelo349Calculator.cuadrar_con_303(
            operaciones_349=ops,
            casillas_303={},
        )
        assert cuadre.cuadre_ok is True
        assert cuadre.diff_servicios_prestados == 7_500
        assert cuadre.diff_servicios_adquiridos == 3_000

    def test_tolerancia_default_es_05(self) -> None:
        assert CUADRE_TOLERANCIA_EUR == 0.5


# --------------------------------------------------------------------------- #
# Integration test (skip por defecto)
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vies_real_endpoint_skipif_no_network() -> None:
    """Test de integracion real contra VIES — solo en CI con red disponible."""
    calc = Modelo349Calculator()
    # Google Ireland NIF-IVA real, valido y publico.
    result = await calc.validate_nif_iva_vies("IE9825613N", fail_open=True)
    # Aceptamos cualquier respuesta no-error: VIES suele caerse fines de semana.
    assert result["nif_iva"] == "IE9825613N"
    assert result["country"] == "IE"
