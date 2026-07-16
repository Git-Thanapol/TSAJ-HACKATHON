"""M2 vision tests. No torch/ultralytics needed: model is faked, cache is files."""
import json

import pytest
from fastapi.testclient import TestClient

from main import create_app
from records.store import verify_chain
from vision import yolo_service

CID = "MSKU1234565"  # valid ISO 6346 check digit

ZONE = {
    "image": f"photos/{CID}/door.jpg",
    "component": "door",
    "concern": "dent",
    "bbox": [0.5, 0.5, 0.2, 0.1],
    "confidence": None,
    "source": "vision",
}


@pytest.fixture()
def assets(tmp_path):
    manifest = {CID: [{"file": f"photos/{CID}/door.jpg", "component": "door"}]}
    (tmp_path / "photos.json").write_text(json.dumps(manifest))
    (tmp_path / "vision_cache.json").write_text(json.dumps({ZONE["image"]: [ZONE]}))
    return tmp_path


@pytest.fixture()
def client(tmp_path, assets, monkeypatch):
    monkeypatch.setenv("WEIGHTS_PATH", str(tmp_path / "nonexistent.pt"))
    app = create_app(db_path=str(tmp_path / "v.db"), assets_dir=str(assets))
    return TestClient(app)


def _start(client, container_id=CID):
    r = client.post("/v0/inspections", json={
        "container_id": container_id, "direction": "inbound", "standard": "IICL-6",
    })
    assert r.status_code == 201
    return r.json()["inspection_id"]


# --- service layer ---

def test_run_zoning_serves_cache_without_weights(assets, monkeypatch):
    monkeypatch.setenv("WEIGHTS_PATH", str(assets / "nope.pt"))
    photos = [{"file": ZONE["image"], "component": "door"}]
    zones = yolo_service.run_zoning(photos, str(assets))
    assert zones == [ZONE]


def test_run_zoning_no_weights_no_cache_raises(assets, monkeypatch):
    monkeypatch.setenv("WEIGHTS_PATH", str(assets / "nope.pt"))
    photos = [{"file": "photos/OTHER/roof.jpg", "component": "roof"}]
    with pytest.raises(yolo_service.VisionUnavailable):
        yolo_service.run_zoning(photos, str(assets))


class _FakeBox:
    def __init__(self, cls, conf, xywhn):
        self.cls, self.conf = cls, conf
        self.xywhn = [xywhn]


class _FakeResult:
    names = {0: "Dent", 1: "Hole", 2: "Rust"}
    boxes = [_FakeBox(0, 0.87, [0.4, 0.5, 0.3, 0.2]), _FakeBox(2, 0.55, [0.1, 0.2, 0.1, 0.1])]


class _FakeModel:
    def predict(self, path, verbose=False):
        return [_FakeResult()]


def test_run_zoning_fresh_uses_model_and_refreshes_cache(assets, monkeypatch):
    monkeypatch.setattr(yolo_service, "_load_model", lambda: _FakeModel())
    photos = [{"file": ZONE["image"], "component": "door"}]
    zones = yolo_service.run_zoning(photos, str(assets), fresh=True)
    assert [z["concern"] for z in zones] == ["dent", "rust"]
    assert all(z["source"] == "vision" and z["component"] == "door" for z in zones)
    # zoning only: no verdicts anywhere in the output
    assert not any({"result", "pass", "fail", "decision"} & set(z) for z in zones)
    # cache refreshed on disk
    cache = json.loads((assets / "vision_cache.json").read_text())
    assert len(cache[ZONE["image"]]) == 2


# --- API layer ---

def test_run_vision_returns_zones_and_appends_event(client):
    iid = _start(client)
    r = client.post(f"/v0/inspections/{iid}/run-vision")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "vision_done"
    assert body["zones"] == [ZONE]
    assert body["photos"][0]["url"] == f"/assets/photos/{CID}/door.jpg"

    h = client.get(f"/v0/containers/{CID}/history").json()
    types = [e["type"] for e in h["events"]]
    assert types == ["inspection.started", "vision.completed"]
    assert h["events"][1]["payload"]["zones"] == [ZONE]


def test_run_vision_rerun_appends_new_event_chain_intact(client):
    iid = _start(client)
    client.post(f"/v0/inspections/{iid}/run-vision")
    client.post(f"/v0/inspections/{iid}/run-vision")
    h = client.get(f"/v0/containers/{CID}/history").json()
    assert [e["type"] for e in h["events"]] == [
        "inspection.started", "vision.completed", "vision.completed",
    ]
    events = [
        {
            **e,
            "container_id": CID,
            "payload_json": json.dumps(e["payload"], sort_keys=True, separators=(",", ":")),
        }
        for e in h["events"]
    ]
    ok, bad = verify_chain(events)
    assert ok, f"chain broken at {bad}"


def test_run_vision_fresh_without_weights_503(client):
    iid = _start(client)
    r = client.post(f"/v0/inspections/{iid}/run-vision?fresh=true")
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "vision_unavailable"


def test_run_vision_no_demo_photos_422(client):
    iid = _start(client, container_id="CSQU3054383")
    r = client.post(f"/v0/inspections/{iid}/run-vision")
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_demo_photos"


def test_run_vision_unknown_inspection_404(client):
    assert client.post("/v0/inspections/insp_nope/run-vision").status_code == 404


def test_run_vision_pushes_ws_update(client):
    iid = _start(client)
    with client.websocket_connect("/v0/live") as ws:
        client.post(f"/v0/inspections/{iid}/run-vision")
        msg = ws.receive_json()
    assert msg["type"] == "vision.zones"
    assert msg["inspection_id"] == iid
    assert msg["zones"] == [ZONE]


def test_meta_lists_standards_and_demo_containers(client):
    r = client.get("/v0/meta")
    assert r.status_code == 200
    body = r.json()
    assert {"IICL-6", "Domestic-Lite"} <= {s["name"] for s in body["standards"]}
    assert body["demo_containers"] == [{"container_id": CID, "photos": 1}]
