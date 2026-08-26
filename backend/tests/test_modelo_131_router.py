"""
Tests for the public Modelo 131 endpoint — POST /api/modelo-131/calculate.

Foco: la casilla [09] (minoración del art. 110.3.c RIRPF) tiene que distinguir
"dato no facilitado" de "cero explícito" también a través de la API, no sólo en
la calculadora. El endpoint es público (lead magnet SEO) y lo consume la
calculadora del frontend, así que un default equivocado aquí se traduce en
importes mal calculados para cualquiera que entre desde la web.
"""

import pytest
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.routers.modelo_131 import router
from app.security.rate_limiter import limiter


@pytest.fixture
def client():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, lambda request, exc: Response(status_code=429))
    app.include_router(router)
    return TestClient(app)


_BASE_BODY = {
    "trimestre": 1,
    "actividad_tipo": "empresarial",
    "rendimiento_neto_modulos_anual": 18000,
    "num_asalariados": 0,
}


def test_endpoint_sin_rendimiento_anterior_no_aplica_minoracion(client):
    """Campo omitido → el request model lo deja en None → sin minoración.

    Art. 110.3.c) RIRPF: la deducción exige que CONSTE que los rendimientos
    netos del ejercicio anterior no excedieron de 12.000 EUR. Si el cliente no
    manda el campo no consta, y aplicarla por defecto rebajaría el pago
    fraccionado de cualquiera que no lo rellene.
    """
    resp = client.post("/api/modelo-131/calculate", json=dict(_BASE_BODY))
    assert resp.status_code == 200
    body = resp.json()
    assert body["desglose"]["minoracion_rendimientos_bajos"] == 0.0
    assert body["desglose"]["rendimiento_neto_anterior"] is None
    # 18.000 × 2% = 360, sin minoración
    assert body["resultado_final"] == 360.0


def test_endpoint_null_explicito_equivale_a_omitido(client):
    """Mandar null explícito es lo mismo que omitir el campo."""
    resp = client.post(
        "/api/modelo-131/calculate",
        json={**_BASE_BODY, "rendimiento_neto_anterior": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["desglose"]["minoracion_rendimientos_bajos"] == 0.0
    assert body["resultado_final"] == 360.0


def test_endpoint_cero_explicito_si_aplica_minoracion(client):
    """Un 0 explícito es un dato y da derecho a los 100 EUR del primer tramo.

    Art. 110.3.c) RIRPF, primer tramo: "Igual o inferior a 9.000 euros ... 100".
    Cero es igual o inferior a 9.000 y la norma no lo excluye.
    """
    resp = client.post(
        "/api/modelo-131/calculate",
        json={**_BASE_BODY, "rendimiento_neto_anterior": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["desglose"]["minoracion_rendimientos_bajos"] == 100.0
    assert body["desglose"]["rendimiento_neto_anterior"] == 0.0
    # 360 − 100 = 260
    assert body["resultado_final"] == 260.0


def test_endpoint_tramo_intermedio(client):
    """11.500 EUR cae en el tramo 11.000,01-12.000 → 25 EUR/trimestre."""
    resp = client.post(
        "/api/modelo-131/calculate",
        json={**_BASE_BODY, "rendimiento_neto_anterior": 11500},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["desglose"]["minoracion_rendimientos_bajos"] == 25.0
    assert body["resultado_final"] == 335.0


def test_endpoint_ignora_pagos_anteriores_de_un_cliente_antiguo(client):
    """Un frontend sin actualizar sigue mandando `pagos_anteriores`: se ignora.

    El 131 no es acumulativo, así que ese concepto no existe en el modelo:
    art. 110.1.b) RIRPF calcula sobre "los datos-base del primer día del año",
    y el mandato de descontar lo ingresado en trimestres anteriores está en la
    letra a) —estimación directa, Modelo 130—, acotado a "lo dispuesto EN ESTA
    LETRA". El diseño de registro DR131_2026 no tiene casilla para él.

    Se ignora en silencio, no se rechaza: devolver 422 rompería a los clientes
    ya desplegados sin ganar nada, porque el resultado correcto es calculable
    sin ese dato. Lo que NO puede pasar es que siga restándose — hacía que el
    contribuyente ingresara de menos.
    """
    resp = client.post(
        "/api/modelo-131/calculate",
        json={**_BASE_BODY, "trimestre": 3, "pagos_anteriores": 500},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 18.000 × 2 % = 360 EUR, los mismos que en el 1T y sin restar los 500.
    assert body["resultado_final"] == 360.0
    assert "10_pagos_anteriores" not in body["casillas"]


def test_pagos_anteriores_no_esta_en_el_schema_del_endpoint():
    """El request model no debe volver a declararlo, ni siquiera inerte.

    Un campo formal reaparece en el OpenAPI del endpoint público, y de ahí al
    formulario de la calculadora web. Es el camino por el que el campo
    regresaría aunque la aritmética siguiera siendo correcta.
    """
    from app.routers.modelo_131 import Modelo131Request

    assert "pagos_anteriores" not in Modelo131Request.model_fields
