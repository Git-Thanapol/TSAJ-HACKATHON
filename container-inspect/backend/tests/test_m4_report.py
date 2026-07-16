"""M4: PDF report rendered from the JSON record + record/list endpoints."""
import json

import pytest
from fastapi.testclient import TestClient

import webhooks
from main import create_app
from records.report import render_pdf

CID = "MSKU1234565"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    manifest = {CID: [{"file": f"photos/{CID}/door.jpg", "component": "door"}]}
    (tmp_path / "photos.json").write_text(json.dumps(manifest))
    (tmp_path / "vision_cache.json").write_text(json.dumps({
        f"photos/{CID}/door.jpg": [{
            "image": f"photos/{CID}/door.jpg", "component": "door", "concern": "dent",
            "bbox": [0.5, 0.5, 0.2, 0.1], "confidence": None, "source": "vision",
        }],
    }))
    monkeypatch.setenv("WEIGHTS_PATH", str(tmp_path / "none.pt"))
    monkeypatch.setattr(webhooks, "fire", lambda *a, **k: {"delivered": True})
    app = create_app(db_path=str(tmp_path / "m4.db"), assets_dir=str(tmp_path))
    return TestClient(app)


def _signed(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "IICL-6",
    })
    iid = r.json()["inspection_id"]
    client.post(f"/v0/inspections/{iid}/run-vision")
    client.post(f"/v0/inspections/{iid}/run-metrology")
    client.post(f"/v0/inspections/{iid}/sign", json={"signed_by": "user:117"})
    return iid


def test_render_pdf_returns_pdf_bytes():
    pdf = render_pdf({
        "inspection_id": "insp_x", "container_id": CID, "direction": "inbound",
        "standard": {"name": "IICL-6", "version": "2016-08-01"}, "status": "signed",
        "signed_by": "user:117", "signed_at": "2026-07-14T00:00:00+00:00",
        "prev_hash": "0" * 64, "hash": "f" * 64,
        "findings": [{
            "component": "side_panel_left", "concern": "dent", "zone_source": "vision",
            "measurement": {"value_mm": 41.0, "limit_mm": 35.0, "source": "metrology", "result": "concern"},
            "decision_source": "metrology", "human_override": False,
            "result": "concern", "note": None, "evidence": ["img.jpg"],
        }],
    })
    assert pdf.startswith(b"%PDF")


def test_report_endpoint_serves_pdf(client):
    iid = _signed(client)
    r = client.get(f"/v0/inspections/{iid}/report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_report_before_sign_409(client):
    r = client.post("/v0/inspections", json={
        "container_id": CID, "direction": "inbound", "standard": "IICL-6",
    })
    iid = r.json()["inspection_id"]
    r = client.get(f"/v0/inspections/{iid}/report.pdf")
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "not_signed"


def test_record_endpoint_returns_chain_hashes(client):
    iid = _signed(client)
    r = client.get(f"/v0/inspections/{iid}/record")
    assert r.status_code == 200
    record = r.json()["record"]
    assert record["status"] == "signed"
    assert record["hash"] and record["prev_hash"]

    h = client.get(f"/v0/containers/{CID}/history").json()
    assert h["events"][-1]["hash"] == record["hash"]


def test_list_inspections(client):
    iid = _signed(client)
    r = client.get("/v0/inspections")
    assert r.status_code == 200
    items = r.json()["inspections"]
    assert items[0]["inspection_id"] == iid
    assert items[0]["status"] == "signed"
