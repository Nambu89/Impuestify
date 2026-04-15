from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_defensia_health_route_exists():
    r = client.get("/api/defensia/_health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "module": "defensia"}
