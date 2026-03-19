"""Tests for creator-specific fields in IRPF estimate endpoint.

Tests cover:
- IRPFEstimateRequest field parsing and defaults
- Platform income aggregation (plataformas_ingresos → ingresos_actividad)
- Granular expense aggregation (gastos_* → gastos_actividad)
- Withholding tax accumulation (withholding_tax_pagado → retenciones_actividad)
- Modelo 349 flag logic
- IAE passthrough
- Backward compatibility (no creator fields → same result as before)
- Full YouTuber scenario end-to-end

All tests mock IRPFSimulator so no live Turso/DB connection is required.
"""
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.routers.irpf_estimate import IRPFEstimateRequest, IRPFEstimateResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_simulator_result(**overrides) -> dict:
    """Build a minimal simulator result dict."""
    defaults = {
        "success": True,
        "cuota_diferencial": 0.0,
        "cuota_total": 0.0,
        "total_retenciones": 0.0,
        "base_imponible_general": 0.0,
        "base_imponible_ahorro": 0.0,
        "cuota_integra_general": 0.0,
        "cuota_integra_ahorro": 0.0,
        "deduccion_ceuta_melilla": 0.0,
        "reduccion_planes_pensiones": 0.0,
        "deduccion_vivienda_pre2013": 0.0,
        "deduccion_maternidad": 0.0,
        "deduccion_familia_numerosa": 0.0,
        "deduccion_donativos": 0.0,
        "total_deducciones_cuota": 0.0,
        "reduccion_tributacion_conjunta": 0.0,
        "deduccion_alquiler_pre2015": 0.0,
        "renta_imputada_inmuebles": 0.0,
        "ganancias_juegos_netas": 0.0,
        "gravamen_especial_loterias": 0.0,
        "deducciones_autonomicas_total": 0.0,
        "mpyf": {},
        "trabajo": {},
        "actividad": {},
    }
    defaults.update(overrides)
    return defaults


async def _call_endpoint(body: IRPFEstimateRequest) -> IRPFEstimateResponse:
    """
    Call the estimate_irpf endpoint logic directly with mocked dependencies.

    Patches:
    - IRPFSimulator.simulate → returns minimal mock result
    - get_db_client → returns a MagicMock DB
    - normalize_ccaa → identity
    - get_deduction_service → returns mock that yields empty lists
    - TokenData (current_user) — not needed here (we call the function directly)
    """
    from app.routers.irpf_estimate import estimate_irpf

    mock_db = MagicMock()
    mock_simulate = AsyncMock(return_value=_make_simulator_result())

    mock_deduction_service = MagicMock()
    mock_deduction_service.evaluate_eligibility = AsyncMock(return_value={
        "eligible": [],
        "maybe_eligible": [],
        "estimated_savings": 0,
        "total_deductions": 0,
    })
    mock_deduction_service.get_missing_questions = AsyncMock(return_value=[])
    mock_deduction_service.compute_ccaa_deduction_amounts = MagicMock(return_value=[])

    # Capture the kwargs passed to simulate for assertions
    captured_kwargs: dict = {}

    async def capturing_simulate(year, **kwargs):
        captured_kwargs.update(kwargs)
        return _make_simulator_result()

    mock_request = MagicMock()  # starlette Request (only needed for rate limiter)

    # Build a real Starlette Request so slowapi is satisfied
    from starlette.testclient import TestClient
    from starlette.requests import Request as StarletteRequest
    from starlette.datastructures import Headers
    from io import BytesIO

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/irpf/estimate",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    real_request = StarletteRequest(scope)
    # slowapi's async wrapper reads/writes request.state.view_rate_limit
    real_request.state.view_rate_limit = None

    with (
        patch("app.utils.irpf_simulator.IRPFSimulator") as MockSimClass,
        patch("app.database.turso_client.get_db_client", new_callable=AsyncMock, return_value=mock_db),
        patch("app.utils.ccaa_constants.normalize_ccaa", side_effect=lambda x: x),
        patch("app.services.deduction_service.get_deduction_service", return_value=mock_deduction_service),
        patch("app.services.deduction_service.DeductionService") as MockDeductionServiceClass,
        # Bypass slowapi rate-limit check — not what we're testing here
        patch("app.security.rate_limiter.limiter._check_request_limit", new_callable=AsyncMock),
    ):
        MockSimClass.return_value.simulate = capturing_simulate
        MockDeductionServiceClass.build_answers_from_profile = MagicMock(return_value={})

        # Inject a dummy current_user — bypass Depends() by calling the function directly
        from app.auth.jwt_handler import TokenData
        dummy_user = TokenData(user_id="test-user", email="test@test.com")

        response = await estimate_irpf(
            request=real_request,
            body=body,
            current_user=dummy_user,
        )

    return response, captured_kwargs


# ---------------------------------------------------------------------------
# T1: platform income sums correctly into ingresos_actividad
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_plataformas_sum():
    """plataformas_ingresos values sum to ingresos_actividad passed to simulator."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        plataformas_ingresos={"youtube": 20000.0, "twitch": 5000.0, "sponsors": 10000.0},
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    assert kwargs["ingresos_actividad"] == pytest.approx(35000.0)


# ---------------------------------------------------------------------------
# T2: granular expenses sum into gastos_actividad
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_gastos_sum():
    """Granular gastos_* fields override gastos_actividad in simulator call."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        gastos_equipo=3000.0,
        gastos_software=500.0,
        gastos_coworking=1200.0,
        gastos_transporte=800.0,
        gastos_formacion=600.0,
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    expected = 3000.0 + 500.0 + 1200.0 + 800.0 + 600.0
    assert kwargs["gastos_actividad"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# T3: withholding tax adds on top of retenciones_actividad
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_withholding_tax():
    """withholding_tax_pagado is added to retenciones_actividad."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        retenciones_actividad=1500.0,
        withholding_tax_pagado=800.0,
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    assert kwargs["retenciones_actividad"] == pytest.approx(2300.0)


# ---------------------------------------------------------------------------
# T4: intracomunitarios > 0 → modelo_349_requerido = True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_modelo_349_required():
    """tiene_ingresos_intracomunitarios + ingresos > 0 → modelo_349_requerido True."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        tiene_ingresos_intracomunitarios=True,
        ingresos_intracomunitarios=5000.0,
    )
    response, _ = await _call_endpoint(body)
    assert response.success is True
    assert response.modelo_349_requerido is True


# ---------------------------------------------------------------------------
# T5: no intracomunitarios → modelo_349_requerido = False
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_modelo_349_not_required():
    """No intracomunitario income → modelo_349_requerido False."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        tiene_ingresos_intracomunitarios=False,
        ingresos_intracomunitarios=0.0,
    )
    response, _ = await _call_endpoint(body)
    assert response.success is True
    assert response.modelo_349_requerido is False


# ---------------------------------------------------------------------------
# T6: epigrafe_iae passthrough into response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_iae_passthrough():
    """epigrafe_iae is returned as iae_seleccionado in the response."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        epigrafe_iae="8690",
    )
    response, _ = await _call_endpoint(body)
    assert response.success is True
    assert response.iae_seleccionado == "8690"


# ---------------------------------------------------------------------------
# T7: empty plataformas_ingresos dict does not crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_empty_platforms():
    """Empty plataformas_ingresos dict does not raise and falls back to body.ingresos_actividad."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        plataformas_ingresos={},
        ingresos_actividad=10000.0,
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    # Empty dict → platform_total = 0 → no override → uses body.ingresos_actividad
    assert kwargs["ingresos_actividad"] == pytest.approx(10000.0)


# ---------------------------------------------------------------------------
# T8: backward compatibility — no creator fields → same as before
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_backward_compat():
    """Request without any creator fields works identically to pre-creator code."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        ingresos_trabajo=40000.0,
        retenciones_trabajo=6000.0,
        ss_empleado=2540.0,
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    # No creator overrides
    assert kwargs["ingresos_actividad"] == pytest.approx(0.0)
    assert kwargs["gastos_actividad"] == pytest.approx(0.0)
    assert kwargs["retenciones_actividad"] == pytest.approx(0.0)
    # Creator response fields are None / False (defaults)
    assert response.plataformas_desglose is None
    assert response.iae_seleccionado is None
    assert response.modelo_349_requerido is False


# ---------------------------------------------------------------------------
# T9: mixed income — trabajo + creator plataformas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_mixed_income():
    """Work income + platform income coexist without interference."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        ingresos_trabajo=30000.0,
        retenciones_trabajo=4500.0,
        plataformas_ingresos={"youtube": 15000.0, "twitch": 5000.0},
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    assert kwargs["ingresos_trabajo"] == pytest.approx(30000.0)
    assert kwargs["ingresos_actividad"] == pytest.approx(20000.0)


# ---------------------------------------------------------------------------
# T10: full YouTuber scenario — 30k YouTube + 10k sponsors + gastos + withholding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_full_scenario():
    """
    Escenario completo YouTuber:
    - 30.000 EUR YouTube + 10.000 EUR sponsors
    - Gastos equipo 5.000 + software 1.200 + coworking 2.400
    - withholding_tax_pagado 2.000
    - epigrafe_iae "8690"
    - ingresos_intracomunitarios 8.000
    """
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        plataformas_ingresos={"youtube": 30000.0, "sponsors": 10000.0},
        gastos_equipo=5000.0,
        gastos_software=1200.0,
        gastos_coworking=2400.0,
        withholding_tax_pagado=2000.0,
        retenciones_actividad=500.0,
        epigrafe_iae="8690",
        tiene_ingresos_intracomunitarios=True,
        ingresos_intracomunitarios=8000.0,
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True

    # Platform total: 40.000
    assert kwargs["ingresos_actividad"] == pytest.approx(40000.0)

    # Gastos: 5000 + 1200 + 2400 = 8600
    assert kwargs["gastos_actividad"] == pytest.approx(8600.0)

    # Retenciones: 500 base + 2000 withholding = 2500
    assert kwargs["retenciones_actividad"] == pytest.approx(2500.0)

    # Response fields
    assert response.iae_seleccionado == "8690"
    assert response.modelo_349_requerido is True
    assert response.plataformas_desglose == {"youtube": 30000.0, "sponsors": 10000.0}


# ---------------------------------------------------------------------------
# T11: negative values in plataformas are ignored (only > 0 counts)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_negative_values():
    """Negative platform values are excluded from the income sum."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        plataformas_ingresos={"youtube": 20000.0, "reimbursement": -500.0, "twitch": 3000.0},
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    # Only positive values sum: 20000 + 3000 = 23000
    assert kwargs["ingresos_actividad"] == pytest.approx(23000.0)


# ---------------------------------------------------------------------------
# T12: non-numeric values in plataformas are ignored
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_invalid_platform_values():
    """Non-numeric values in plataformas_ingresos are ignored (isinstance guard)."""
    body = IRPFEstimateRequest(
        comunidad_autonoma="Madrid",
        plataformas_ingresos={
            "youtube": 15000.0,
            "notes": "pending invoicing",  # string — should be ignored
            "twitch": 5000.0,
            "other": None,  # None — should be ignored
        },
    )
    response, kwargs = await _call_endpoint(body)
    assert response.success is True
    # Only numeric positives: 15000 + 5000 = 20000
    assert kwargs["ingresos_actividad"] == pytest.approx(20000.0)
