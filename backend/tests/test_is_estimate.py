"""Tests de los endpoints IS (Modelo 200 + 202)."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# Mock external dependencies before importing app
@pytest.fixture(autouse=True)
def mock_deps():
    """Mock heavy dependencies that are not needed for IS endpoint tests."""
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-key",
        "TURSO_DATABASE_URL": "libsql://test.turso.io",
        "TURSO_AUTH_TOKEN": "test-token",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-32chars!",
    }):
        with patch("app.database.turso_client.get_db_client", new_callable=AsyncMock):
            yield


@pytest.fixture
def client(mock_deps):
    """FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.routers.is_estimate import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestISEstimateEndpoint:
    """POST /api/irpf/is-estimate"""

    def test_sl_basica_madrid(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_imponible"] == 100_000
        assert data["cuota_integra"] == 25_000
        assert data["tipo"] == "a_ingresar"
        assert "disclaimer" in data

    def test_pyme_tramos(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "facturacion_anual": 800_000,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        # 50k * 23% + 50k * 25% = 11500 + 12500 = 24000
        assert data["cuota_integra"] == 24_000

    def test_nueva_creacion(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "tipo_entidad": "nueva_creacion",
            "ejercicios_con_bi_positiva": 1,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        # 50k * 15% + 50k * 20% = 7500 + 10000 = 17500
        assert data["cuota_integra"] == 17_500

    def test_foral_bizkaia(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "Bizkaia",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuota_integra"] == 24_000
        assert data["regimen"] == "foral_bizkaia"

    def test_zec_canarias(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "Canarias",
            "es_zec": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuota_integra"] == 4_000
        assert data["regimen"] == "zec_canarias"

    def test_ceuta_melilla_bonificacion(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "Melilla",
            "rentas_ceuta_melilla": 100_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["bonificaciones_total"] == 12_500
        assert data["cuota_liquida"] == 12_500

    def test_resultado_negativo(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": -50_000,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_imponible"] == 0
        assert data["bin_generada"] == 50_000
        assert data["cuota_integra"] == 0

    def test_includes_202_both_modalities(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "pago_202_art40_2" in data
        assert "pago_202_art40_3" in data
        # art40_2: 18% of (25000 cuota - 0 deducciones - 0 retenciones)
        assert data["pago_202_art40_2"] == 4_500

    def test_ingresos_menos_gastos(self, client):
        resp = client.post("/api/irpf/is-estimate", json={
            "ingresos_explotacion": 300_000,
            "gastos_explotacion": 200_000,
            "territorio": "Madrid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resultado_contable"] == 100_000
        assert data["cuota_integra"] == 25_000

    def test_invalid_territory_still_works(self, client):
        """normalize_ccaa should handle unknown territory gracefully."""
        resp = client.post("/api/irpf/is-estimate", json={
            "resultado_contable": 100_000,
            "territorio": "madrid",  # lowercase
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuota_integra"] == 25_000

    def test_missing_required_fields_uses_defaults(self, client):
        """All fields have defaults, so empty body should work."""
        resp = client.post("/api/irpf/is-estimate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuota_integra"] == 0


class TestIS202Endpoint:
    """POST /api/irpf/is-202"""

    def test_art40_2_basico(self, client):
        resp = client.post("/api/irpf/is-202", json={
            "modalidad": "art40_2",
            "cuota_integra_ultimo": 50_000,
            "deducciones_bonificaciones_ultimo": 5_000,
            "retenciones_ultimo": 3_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 18% of (50000 - 5000 - 3000) = 18% of 42000 = 7560
        assert data["pago_trimestral"] == 7_560
        assert data["modalidad"] == "art40_2"
        assert "calendario" in data
        assert len(data["calendario"]) == 3

    def test_art40_3_basico(self, client):
        resp = client.post("/api/irpf/is-202", json={
            "modalidad": "art40_3",
            "base_imponible_periodo": 100_000,
            "facturacion_anual": 5_000_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 17% of 100000 = 17000
        assert data["pago_trimestral"] == 17_000
        assert data["porcentaje_aplicado"] == 17.0

    def test_art40_3_grande(self, client):
        resp = client.post("/api/irpf/is-202", json={
            "modalidad": "art40_3",
            "base_imponible_periodo": 100_000,
            "facturacion_anual": 15_000_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        # >10M: 24% of 100000 = 24000
        assert data["pago_trimestral"] == 24_000
        assert data["porcentaje_aplicado"] == 24.0

    def test_disclaimer_present(self, client):
        resp = client.post("/api/irpf/is-202", json={
            "modalidad": "art40_2",
            "cuota_integra_ultimo": 10_000,
        })
        assert resp.status_code == 200
        assert "disclaimer" in resp.json()
