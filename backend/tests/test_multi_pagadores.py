"""
Tests for multi-pagador support in IRPF estimation.

Covers:
- PagadorItem model validation
- Aggregation logic (pagadores → ingresos_trabajo totals)
- Obligacion de declarar (Art. 96 LIRPF)
- Retrocompatibility (empty pagadores → existing behavior)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.routers.irpf_estimate import (
    PagadorItem,
    IRPFEstimateRequest,
    ObligacionDeclarar,
    _calcular_obligacion_declarar,
    OBLIGACION_LIMITES,
)


# ============================================================
# PagadorItem model tests
# ============================================================

class TestPagadorItem:
    """Tests for PagadorItem Pydantic model."""

    def test_default_values(self):
        p = PagadorItem()
        assert p.nombre == ""
        assert p.nif is None
        assert p.clave == "empleado"
        assert p.retribuciones_dinerarias == 0
        assert p.retenciones == 0
        assert p.gastos_deducibles == 0
        assert p.retribuciones_especie == 0
        assert p.ingresos_cuenta == 0

    def test_with_values(self):
        p = PagadorItem(
            nombre="DEVOTEAM DRAGO SAU",
            nif="B73737553",
            clave="empleado",
            retribuciones_dinerarias=22300.99,
            retenciones=4046.27,
            gastos_deducibles=1445.00,
        )
        assert p.nombre == "DEVOTEAM DRAGO SAU"
        assert p.nif == "B73737553"
        assert p.retribuciones_dinerarias == 22300.99
        assert p.retenciones == 4046.27
        assert p.gastos_deducibles == 1445.00

    def test_clave_values(self):
        for clave in ["empleado", "pensionista", "desempleo", "otro"]:
            p = PagadorItem(clave=clave)
            assert p.clave == clave

    def test_retribuciones_especie(self):
        p = PagadorItem(
            retribuciones_dinerarias=20000,
            retribuciones_especie=3000,
            ingresos_cuenta=500,
        )
        total = p.retribuciones_dinerarias + p.retribuciones_especie + p.ingresos_cuenta
        assert total == 23500


# ============================================================
# IRPFEstimateRequest multi-pagador tests
# ============================================================

class TestIRPFEstimateRequestMultiPagador:
    """Tests for multi-pagador fields in IRPFEstimateRequest."""

    def test_default_no_pagadores(self):
        req = IRPFEstimateRequest(comunidad_autonoma="Madrid")
        assert req.pagadores == []
        assert req.num_pagadores == 1

    def test_with_pagadores(self):
        pagadores = [
            PagadorItem(nombre="Empresa A", retribuciones_dinerarias=20000, retenciones=3000, gastos_deducibles=1200),
            PagadorItem(nombre="Empresa B", retribuciones_dinerarias=10000, retenciones=1500, gastos_deducibles=600),
        ]
        req = IRPFEstimateRequest(
            comunidad_autonoma="Madrid",
            pagadores=pagadores,
            num_pagadores=2,
        )
        assert len(req.pagadores) == 2
        assert req.num_pagadores == 2

    def test_retrocompat_ingresos_trabajo_directo(self):
        """Without pagadores, ingresos_trabajo should be used directly."""
        req = IRPFEstimateRequest(
            comunidad_autonoma="Madrid",
            ingresos_trabajo=30000,
            retenciones_trabajo=5000,
            ss_empleado=2000,
        )
        assert req.ingresos_trabajo == 30000
        assert req.pagadores == []


# ============================================================
# Aggregation logic tests
# ============================================================

class TestMultiPagadorAggregation:
    """Tests for aggregating pagador totals."""

    def _aggregate(self, pagadores):
        """Simulate aggregation logic from irpf_estimate endpoint."""
        ingresos = sum(
            p.retribuciones_dinerarias + p.retribuciones_especie + p.ingresos_cuenta
            for p in pagadores
        )
        retenciones = sum(p.retenciones for p in pagadores)
        ss = sum(p.gastos_deducibles for p in pagadores)
        return ingresos, retenciones, ss

    def test_single_pagador(self):
        pagadores = [
            PagadorItem(retribuciones_dinerarias=30000, retenciones=5000, gastos_deducibles=2000),
        ]
        ingresos, retenciones, ss = self._aggregate(pagadores)
        assert ingresos == 30000
        assert retenciones == 5000
        assert ss == 2000

    def test_three_pagadores(self):
        """Real case from AEAT screenshots: 3 employers."""
        pagadores = [
            PagadorItem(nombre="DEVOTEAM DRAGO SAU", retribuciones_dinerarias=22300.99, retenciones=4046.27, gastos_deducibles=1445.00),
            PagadorItem(nombre="SVAN TRADING SL", retribuciones_dinerarias=8535.74, retenciones=1114.78, gastos_deducibles=553.67),
            PagadorItem(nombre="PAGADURIA HABERES MDE", retribuciones_dinerarias=2.81, retenciones=0.42, gastos_deducibles=0.07),
        ]
        ingresos, retenciones, ss = self._aggregate(pagadores)
        assert round(ingresos, 2) == 30839.54
        assert round(retenciones, 2) == 5161.47
        assert round(ss, 2) == 1998.74

    def test_pagadores_con_especie(self):
        """Pagadores with retribuciones en especie (company car, insurance, etc.)."""
        pagadores = [
            PagadorItem(retribuciones_dinerarias=25000, retribuciones_especie=3000, retenciones=4200, gastos_deducibles=1600),
            PagadorItem(retribuciones_dinerarias=5000, retenciones=750, gastos_deducibles=300),
        ]
        ingresos, retenciones, ss = self._aggregate(pagadores)
        assert ingresos == 33000  # 25000+3000+5000
        assert retenciones == 4950
        assert ss == 1900

    def test_empty_pagadores_returns_zero(self):
        ingresos, retenciones, ss = self._aggregate([])
        assert ingresos == 0
        assert retenciones == 0
        assert ss == 0


# ============================================================
# Obligacion de declarar tests (Art. 96 LIRPF)
# ============================================================

class TestObligacionDeclarar:
    """Tests for _calcular_obligacion_declarar function."""

    def _make_body(self, **kwargs):
        defaults = {
            "comunidad_autonoma": "Madrid",
            "pagadores": [],
        }
        defaults.update(kwargs)
        return IRPFEstimateRequest(**defaults)

    def test_un_pagador_bajo_limite_no_obligado(self):
        body = self._make_body()
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=20000, num_pagadores=1)
        assert result["obligado"] is False
        assert result["limite_aplicable"] == 22000

    def test_un_pagador_sobre_limite_obligado(self):
        body = self._make_body()
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=25000, num_pagadores=1)
        assert result["obligado"] is True
        assert "22.000" in result["motivo"] or "22,000" in result["motivo"] or "22000" in result["motivo"]

    def test_dos_pagadores_segundo_mayor_1500_obligado(self):
        """2 pagadores, 2o > 1.500 EUR, total > 15.876 → obligado."""
        pagadores = [
            PagadorItem(retribuciones_dinerarias=14000),
            PagadorItem(retribuciones_dinerarias=5000),
        ]
        body = self._make_body(pagadores=pagadores)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=19000, num_pagadores=2)
        assert result["obligado"] is True
        assert result["limite_aplicable"] == 15876

    def test_dos_pagadores_segundo_menor_1500_no_obligado(self):
        """2 pagadores, 2o < 1.500 EUR → aplica limite 22.000, no obligado si total < 22.000."""
        pagadores = [
            PagadorItem(retribuciones_dinerarias=18000),
            PagadorItem(retribuciones_dinerarias=1000),
        ]
        body = self._make_body(pagadores=pagadores)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=19000, num_pagadores=2)
        assert result["obligado"] is False
        assert result["limite_aplicable"] == 22000

    def test_tres_pagadores_suma_secundarios_mayor_1500(self):
        """3 pagadores: 2o+3o sum > 1.500 → obligado if total > 15.876."""
        pagadores = [
            PagadorItem(retribuciones_dinerarias=14000),
            PagadorItem(retribuciones_dinerarias=800),
            PagadorItem(retribuciones_dinerarias=1200),
        ]
        body = self._make_body(pagadores=pagadores)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=16000, num_pagadores=3)
        assert result["obligado"] is True
        assert result["limite_aplicable"] == 15876

    def test_rendimientos_capital_obligan(self):
        """Rendimientos capital > 1.600 EUR obligan siempre."""
        body = self._make_body(intereses=1000, dividendos=700)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=10000, num_pagadores=1)
        assert result["obligado"] is True

    def test_rentas_inmobiliarias_obligan(self):
        """Rentas inmobiliarias > 1.000 EUR obligan siempre."""
        body = self._make_body(ingresos_alquiler=1500)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=10000, num_pagadores=1)
        assert result["obligado"] is True

    def test_sin_pagadores_con_num_pagadores_2(self):
        """When num_pagadores > 1 but no pagadores list, assume obligation."""
        body = self._make_body()
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=18000, num_pagadores=2)
        assert result["obligado"] is True
        assert result["limite_aplicable"] == 15876

    def test_caso_real_aeat_screenshots(self):
        """Real case from user's AEAT app: 3 pagadores, 30.839,54 EUR total."""
        pagadores = [
            PagadorItem(nombre="DEVOTEAM", retribuciones_dinerarias=22300.99),
            PagadorItem(nombre="SVAN TRADING", retribuciones_dinerarias=8535.74),
            PagadorItem(nombre="PAGADURIA MDE", retribuciones_dinerarias=2.81),
        ]
        body = self._make_body(pagadores=pagadores)
        result = _calcular_obligacion_declarar(body, ingresos_trabajo=30839.54, num_pagadores=3)
        assert result["obligado"] is True
        # 2o+3o = 8535.74+2.81 = 8538.55 > 1500 → limite 15.876
        assert result["limite_aplicable"] == 15876

    def test_limites_constantes_existen(self):
        """Verify OBLIGACION_LIMITES has expected structure."""
        assert 2025 in OBLIGACION_LIMITES
        limites = OBLIGACION_LIMITES[2025]
        assert limites["un_pagador"] == 22000
        assert limites["multi_pagador"] == 15876
        assert limites["segundo_pagador_minimo"] == 1500
        assert limites["rentas_inmobiliarias"] == 1000
        assert limites["rendimientos_capital"] == 1600


# ============================================================
# ObligacionDeclarar response model tests
# ============================================================

class TestObligacionDeclarModel:
    """Tests for ObligacionDeclarar Pydantic model."""

    def test_defaults(self):
        od = ObligacionDeclarar()
        assert od.obligado is False
        assert od.motivo == ""
        assert od.limite_aplicable == 22000

    def test_with_values(self):
        od = ObligacionDeclarar(
            obligado=True,
            motivo="2 pagadores superan limite",
            limite_aplicable=15876,
        )
        assert od.obligado is True
        assert "2 pagadores" in od.motivo
        assert od.limite_aplicable == 15876
