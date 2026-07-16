import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "s.db"))
    return TestClient(app)


def _start(client):
    r = client.post("/v0/inspections", json={
        "container_id": "MSKU1234565", "direction": "inbound", "standard": "IICL-6",
    })
    return r.json()["inspection_id"]


def test_stub_unknown_inspection_404(client):
    r = client.post("/v0/inspections/insp_nope/run-vision")
    assert r.status_code == 404


def test_ws_echo(client):
    with client.websocket_connect("/v0/live") as ws:
        ws.send_text("ping")
        assert ws.receive_json() == {"echo": "ping"}


def test_fusion_precedence_constant():
    from fusion import PRECEDENCE
    assert PRECEDENCE == ("human", "metrology", "vision")
