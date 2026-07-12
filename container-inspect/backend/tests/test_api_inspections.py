import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "api.db"))
    return TestClient(app)


BODY = {"container_id": "MSKU1234565", "direction": "inbound", "standard": "IICL-6"}


def test_start_inspection(client):
    r = client.post("/v0/inspections", json=BODY)
    assert r.status_code == 201
    data = r.json()
    assert data["inspection_id"].startswith("insp_")
    assert data["standard"] == {"name": "IICL-6", "version": "2016-08-01"}
    assert data["status"] == "started"
    assert data["event_id"].startswith("evt_")


def test_bad_check_digit_422(client):
    r = client.post("/v0/inspections", json={**BODY, "container_id": "MSKU1234560"})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_container_id"


def test_unknown_standard_422_lists_profiles(client):
    r = client.post("/v0/inspections", json={**BODY, "standard": "CSC-Plus"})
    assert r.status_code == 422
    assert r.json()["detail"]["available"] == ["Domestic-Lite", "IICL-6"]


def test_history_roundtrip_and_chain(client):
    client.post("/v0/inspections", json=BODY)
    client.post("/v0/inspections", json={**BODY, "direction": "outbound"})
    r = client.get("/v0/containers/MSKU1234565/history")
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 2
    assert events[0]["prev_hash"] == "0" * 64
    assert events[1]["prev_hash"] == events[0]["hash"]
    assert events[0]["payload"]["direction"] == "inbound"
    assert events[0]["type"] == "inspection.started"


def test_history_empty_container(client):
    r = client.get("/v0/containers/CSQU3054383/history")
    assert r.status_code == 200
    assert r.json()["events"] == []


def test_idempotency_replay(client):
    h = {"Idempotency-Key": "gate-fire-001"}
    r1 = client.post("/v0/inspections", json=BODY, headers=h)
    r2 = client.post("/v0/inspections", json=BODY, headers=h)
    assert r1.json()["inspection_id"] == r2.json()["inspection_id"]
    assert r2.json()["replayed"] is True
    events = client.get("/v0/containers/MSKU1234565/history").json()["events"]
    assert len(events) == 1  # no duplicate event appended
