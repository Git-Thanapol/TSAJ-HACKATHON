from fastapi.testclient import TestClient

from main import create_app


def test_health(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "container-inspect", "version": "0.1.0"}
