"""M3: mock metrology + rules eval + fusion + sign-off + webhook."""
import json

import pytest
from fastapi.testclient import TestClient

import fusion
import webhooks
from main import create_app

CID = "MSKU1234565"

ZONES = [
    # dent on a measurable component (side_panel rule, limit 35mm)
    {"image": f"photos/{CID}/side_panel_left.jpg", "component": "side_panel_left",
     "concern": "dent", "bbox": [0.5, 0.5, 0.2, 0.1], "confidence": None, "source": "vision"},
    # rust: appearance concern, mm value must NOT decide it
    {"image": f"photos/{CID}/side_panel_left.jpg", "component": "side_panel_left",
     "concern": "rust", "bbox": [0.1, 0.1, 0.1, 0.1], "confidence": None, "source": "vision"},
    # dent on a component with no IICL-6 rule -> human review
    {"image": f"photos/{CID}/door.jpg", "component": "door",
     "concern": "dent", "bbox": [0.4, 0.4, 0.2, 0.2], "confidence": None, "source": "vision"},
]


@pytest.fixture()
def assets(tmp_path):
    manifest = {CID: [
        {"file": f"photos/{CID}/side_panel_left.jpg", "component": "side_panel_left"},
        {"file": f"photos/{CID}/door.jpg", "component": "door"},
    ]}
    (tmp_path / "photos.json").write_text(json.dumps(manifest))
    (tmp_path / "vision_cache.json").write_text(json.dumps({
        f"photos/{CID}/side_panel_left.jpg": ZONES[:2],
        f"photos/{CID}/door.jpg": ZONES[2:],
    }))
    (tmp_path / "measurements.json").write_text(json.dumps({
        CID: {"side_panel_left": 41.0},  # > 35mm limit -> concern
    }))
    return tmp_path


@pytest.fixture()
def client(tmp_path, assets, monkeypatch):
    monkeypatch.setenv("WEIGHTS_PATH", str(tmp_path / "none.pt"))
    app = create_app(db_path=str(tmp_path / "m3.db"), assets_dir=str(assets))
    return TestClient(app)


def _to_signed(client, standard="IICL-6", overrides=None, run_metrology=True):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": standard,
    })
    iid = r.json()["inspection_id"]
    client.post(f"/v0/inspections/{iid}/run-vision")
    if run_metrology:
        client.post(f"/v0/inspections/{iid}/run-metrology")
    r = client.post(f"/v0/inspections/{iid}/sign", json={
        "signed_by": "user:117", "overrides": overrides or [],
    })
    return iid, r


# --- fusion unit ---

def test_reconcile_metrology_decides_measurable():
    ms = [{"component": "side_panel_left", "measure": "internal_cube_intrusion",
           "value_mm": 41.0, "limit_mm": 35.0, "result": "concern", "source": "metrology"}]
    findings = fusion.reconcile(ZONES, ms, [])
    dent = next(f for f in findings if f["component"] == "side_panel_left" and f["concern"] == "dent")
    assert dent["decision_source"] == "metrology"
    assert dent["result"] == "concern"
    assert dent["measurement"]["value_mm"] == 41.0
    assert dent["human_override"] is False


def test_reconcile_rust_and_unruled_fall_to_human():
    ms = [{"component": "side_panel_left", "measure": "internal_cube_intrusion",
           "value_mm": 41.0, "limit_mm": 35.0, "result": "concern", "source": "metrology"}]
    findings = fusion.reconcile(ZONES, ms, [])
    rust = next(f for f in findings if f["concern"] == "rust")
    door = next(f for f in findings if f["component"] == "door")
    for f in (rust, door):
        assert f["decision_source"] == "human"
        assert f["measurement"] is None
        assert f["result"] == "concern"  # stays a concern until a human clears it


def test_reconcile_human_override_wins_and_keeps_measurement():
    ms = [{"component": "side_panel_left", "measure": "internal_cube_intrusion",
           "value_mm": 41.0, "limit_mm": 35.0, "result": "concern", "source": "metrology"}]
    ov = [{"component": "side_panel_left", "concern": "dent", "result": "pass", "note": "old repair, within tolerance"}]
    findings = fusion.reconcile(ZONES, ms, ov)
    dent = next(f for f in findings if f["concern"] == "dent" and f["component"] == "side_panel_left")
    assert dent["decision_source"] == "human"
    assert dent["human_override"] is True
    assert dent["result"] == "pass"
    # the measured value stays on record untouched — evidence, not erasure
    assert dent["measurement"]["result"] == "concern"


def test_precedence_locked():
    assert fusion.PRECEDENCE == ("human", "metrology", "vision")


# --- API: run-metrology ---

def test_run_metrology_evaluates_value_vs_limit(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "IICL-6",
    })
    iid = r.json()["inspection_id"]
    client.post(f"/v0/inspections/{iid}/run-vision")
    r = client.post(f"/v0/inspections/{iid}/run-metrology")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "metrology_done"
    assert body["measurements"] == [{
        "component": "side_panel_left", "rule": "side_panel",
        "measure": "internal_cube_intrusion", "value_mm": 41.0, "limit_mm": 35.0,
        "result": "concern", "source": "metrology",
    }]


def test_run_metrology_before_vision_409(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "IICL-6",
    })
    iid = r.json()["inspection_id"]
    r = client.post(f"/v0/inspections/{iid}/run-metrology")
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "vision_not_run"


def test_run_metrology_appearance_only_returns_no_measurements(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "Domestic-Lite",
    })
    iid = r.json()["inspection_id"]
    client.post(f"/v0/inspections/{iid}/run-vision")
    r = client.post(f"/v0/inspections/{iid}/run-metrology")
    assert r.status_code == 200
    assert r.json()["mode"] == "appearance_only"
    assert r.json()["measurements"] == []


# --- API: sign ---

def test_sign_writes_record_and_fires_webhook(client, monkeypatch):
    fired = []
    monkeypatch.setattr(webhooks, "fire", lambda url, et, payload, timeout=3.0: (
        fired.append((url, et, payload)) or {"url": url, "delivered": True, "status_code": 202}
    ))
    iid, r = _to_signed(client)
    assert r.status_code == 200
    record = r.json()["record"]
    assert record["status"] == "signed"
    assert record["signed_by"] == "user:117"
    assert record["hash"] and record["prev_hash"]
    assert len(record["findings"]) == 3
    assert r.json()["webhook"]["delivered"] is True

    assert fired and fired[0][1] == "inspection.completed"
    assert fired[0][2]["container_id"] == CID

    h = client.get(f"/v0/containers/{CID}/history").json()
    assert [e["type"] for e in h["events"]] == [
        "inspection.started", "vision.completed", "metrology.completed", "inspection.completed",
    ]
    # record in the chain is the source of truth and matches the hash fields
    last = h["events"][-1]
    assert last["hash"] == record["hash"]
    assert last["payload"]["record"]["findings"] == record["findings"]


def test_sign_with_override(client, monkeypatch):
    monkeypatch.setattr(webhooks, "fire", lambda *a, **k: {"delivered": True})
    iid, r = _to_signed(client, overrides=[{
        "component": "side_panel_left", "concern": "dent", "result": "pass", "note": "measured old repair",
    }])
    dent = next(f for f in r.json()["record"]["findings"]
                if f["component"] == "side_panel_left" and f["concern"] == "dent")
    assert dent["human_override"] is True
    assert dent["decision_source"] == "human"
    assert dent["result"] == "pass"


def test_sign_domestic_lite_without_metrology(client, monkeypatch):
    monkeypatch.setattr(webhooks, "fire", lambda *a, **k: {"delivered": True})
    iid, r = _to_signed(client, standard="Domestic-Lite", run_metrology=False)
    assert r.status_code == 200
    assert all(f["decision_source"] == "human" for f in r.json()["record"]["findings"])


def test_sign_before_vision_409(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "IICL-6",
    })
    iid = r.json()["inspection_id"]
    r = client.post(f"/v0/inspections/{iid}/sign", json={"signed_by": "user:117"})
    assert r.status_code == 409


def test_yard_inbox_receives_webhook_payload(client):
    r = client.post("/v0/yard/inbox", json={"event": "inspection.completed", "payload": {"x": 1}})
    assert r.status_code == 202
    r = client.get("/v0/yard/inbox")
    assert r.json()["deliveries"] == [{"event": "inspection.completed", "payload": {"x": 1}}]


def test_webhook_fire_survives_dead_subscriber():
    report = webhooks.fire("http://127.0.0.1:9", "inspection.completed", {}, timeout=0.2)
    assert report["delivered"] is False
