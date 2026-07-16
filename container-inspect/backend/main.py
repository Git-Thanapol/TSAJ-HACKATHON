import json
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import fusion
import webhooks
from metrology import mock as metrology
from models import InspectionRecord, StandardRef, validate_iso6346
from records import report, store
from rules.engine import evaluate, load_rulesets, match_rule
from vision import yolo_service

VERSION = "0.1.0"


class Override(BaseModel):
    component: str
    concern: str | None = None  # None = applies to every concern on the component
    result: Literal["pass", "concern"]
    note: str | None = None


class SignBody(BaseModel):
    signed_by: str
    overrides: list[Override] = []


class WsHub:
    """Live dashboard fan-out for WS /v0/live."""

    def __init__(self):
        self.sockets: set[WebSocket] = set()

    async def broadcast(self, message: dict) -> None:
        for ws in list(self.sockets):
            try:
                await ws.send_json(message)
            except Exception:
                self.sockets.discard(ws)


def load_manifest(assets_dir: str) -> dict:
    """photos.json: {container_id: [{file, component}, ...]} — demo photo sets."""
    try:
        with open(os.path.join(assets_dir, "photos.json"), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class StartInspection(BaseModel):
    container_id: str
    direction: Literal["inbound", "outbound"]
    standard: str


def create_app(
    db_path: str | None = None,
    standards_dir: str | None = None,
    assets_dir: str | None = None,
) -> FastAPI:
    db_path = db_path or os.environ.get("DB_PATH", "/data/inspections.db")
    standards_dir = standards_dir or os.path.join(os.path.dirname(__file__), "standards")
    assets_dir = assets_dir or os.environ.get(
        "ASSETS_DIR", os.path.join(os.path.dirname(__file__), "..", "assets")
    )

    app = FastAPI(title="container-inspect", version=VERSION)
    app.state.db_path = db_path
    app.state.rulesets = load_rulesets(standards_dir)
    app.state.assets_dir = assets_dir
    app.state.manifest = load_manifest(assets_dir)
    app.state.hub = WsHub()
    # dummy "Yard System" receiver: the webhook's default local subscriber (M3/M4)
    app.state.yard_inbox = []
    app.state.webhook_url = os.environ.get(
        "WEBHOOK_URL", "http://localhost:8000/v0/yard/inbox"
    )
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "container-inspect", "version": VERSION}

    @app.post("/v0/inspections", status_code=201)
    def start_inspection(
        body: StartInspection,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        if not validate_iso6346(body.container_id):
            raise HTTPException(422, detail={
                "error": "invalid_container_id",
                "reason": "ISO 6346 format or check digit failed",
            })

        conn = store.get_conn(app.state.db_path)
        try:
            if idempotency_key:
                row = conn.execute(
                    "SELECT i.inspection_id, i.container_id, i.direction, i.standard_name, i.status"
                    " FROM idempotency k JOIN inspections i ON i.inspection_id = k.inspection_id"
                    " WHERE k.key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row:
                    stored_ruleset = app.state.rulesets.get(row["standard_name"])
                    return {
                        "inspection_id": row["inspection_id"],
                        "container_id": row["container_id"],
                        "direction": row["direction"],
                        "standard": {
                            "name": row["standard_name"],
                            "version": stored_ruleset.version if stored_ruleset else None,
                        },
                        "status": row["status"],
                        "event_id": None,
                        "replayed": True,
                    }

            ruleset = app.state.rulesets.get(body.standard)
            if ruleset is None:
                raise HTTPException(422, detail={
                    "error": "unknown_standard",
                    "available": sorted(app.state.rulesets),
                })

            inspection_id = store.make_id("insp")
            conn.execute(
                "INSERT INTO inspections (inspection_id, container_id, direction, standard_name, status, created_at)"
                " VALUES (?, ?, ?, ?, 'started', datetime('now'))",
                (inspection_id, body.container_id, body.direction, body.standard),
            )
            event = store.append_event(
                conn,
                inspection_id=inspection_id,
                container_id=body.container_id,
                type="inspection.started",
                payload={
                    "direction": body.direction,
                    "standard": {"name": ruleset.standard, "version": ruleset.version},
                },
            )
            if idempotency_key:
                conn.execute(
                    "INSERT INTO idempotency (key, inspection_id) VALUES (?, ?)",
                    (idempotency_key, inspection_id),
                )
            # autocommit connection: inspections/idempotency INSERTs commit per statement;
            # append_event manages its own BEGIN IMMEDIATE transaction
            return _response(inspection_id, body, ruleset, event_id=event["event_id"], replayed=False)
        finally:
            conn.close()

    def _response(inspection_id, body, ruleset, *, event_id, replayed):
        return {
            "inspection_id": inspection_id,
            "container_id": body.container_id,
            "direction": body.direction,
            "standard": {"name": ruleset.standard, "version": ruleset.version},
            "status": "started",
            "event_id": event_id,
            "replayed": replayed,
        }

    @app.get("/v0/containers/{container_id}/history")
    def container_history(container_id: str):
        conn = store.get_conn(app.state.db_path)
        try:
            events = store.get_history(conn, container_id)
        finally:
            conn.close()
        return {
            "container_id": container_id,
            "events": [
                {
                    "event_id": e["event_id"],
                    "inspection_id": e["inspection_id"],
                    "type": e["type"],
                    "ts": e["ts"],
                    "payload": json.loads(e["payload_json"]),
                    "prev_hash": e["prev_hash"],
                    "hash": e["hash"],
                }
                for e in events
            ],
        }

    def _require_inspection(inspection_id: str) -> dict:
        conn = store.get_conn(app.state.db_path)
        try:
            row = conn.execute(
                "SELECT inspection_id, container_id, status, direction, standard_name"
                " FROM inspections WHERE inspection_id = ?",
                (inspection_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, detail={"error": "unknown_inspection"})
        return dict(row)

    def _signed_record(conn, inspection_id: str) -> dict:
        """Latest signed record from the hash chain, with its chain hashes."""
        row = conn.execute(
            "SELECT payload_json, prev_hash, hash FROM events"
            " WHERE inspection_id = ? AND type = 'inspection.completed'"
            " ORDER BY seq DESC LIMIT 1",
            (inspection_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(409, detail={
                "error": "not_signed",
                "reason": "no signed record yet: complete the sign-off first",
            })
        record = json.loads(row["payload_json"])["record"]
        record["prev_hash"], record["hash"] = row["prev_hash"], row["hash"]
        return record

    @app.get("/v0/inspections")
    def list_inspections(limit: int = 20):
        conn = store.get_conn(app.state.db_path)
        try:
            rows = conn.execute(
                "SELECT inspection_id, container_id, direction, standard_name, status, created_at"
                " FROM inspections ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return {"inspections": [dict(r) for r in rows]}

    @app.get("/v0/inspections/{inspection_id}/record")
    def get_record(inspection_id: str):
        _require_inspection(inspection_id)
        conn = store.get_conn(app.state.db_path)
        try:
            return {"record": _signed_record(conn, inspection_id)}
        finally:
            conn.close()

    @app.get("/v0/meta")
    def meta():
        """Demo discovery: available standards + containers with pre-recorded photos."""
        return {
            "standards": [
                {"name": name, "version": rs.version, "mode": rs.mode}
                for name, rs in sorted(app.state.rulesets.items())
            ],
            "demo_containers": [
                {"container_id": cid, "photos": len(photos)}
                for cid, photos in sorted(app.state.manifest.items())
            ],
        }

    @app.post("/v0/inspections/{inspection_id}/run-vision")
    async def run_vision(inspection_id: str, fresh: bool = False):
        """YOLO zoning on cached photos. Zones only — vision never emits pass/fail."""
        insp = _require_inspection(inspection_id)
        photos = app.state.manifest.get(insp["container_id"])
        if not photos:
            raise HTTPException(422, detail={
                "error": "no_demo_photos",
                "container_id": insp["container_id"],
                "available": sorted(app.state.manifest),
            })
        try:
            # inference is local (weights on disk) and blocking — keep the event loop free
            zones = await run_in_threadpool(
                yolo_service.run_zoning, photos, app.state.assets_dir, fresh
            )
        except yolo_service.VisionUnavailable as exc:
            raise HTTPException(503, detail={"error": "vision_unavailable", "reason": str(exc)})

        conn = store.get_conn(app.state.db_path)
        try:
            # re-runs append a new event, never overwrite (gates double-fire)
            event = store.append_event(
                conn,
                inspection_id=inspection_id,
                container_id=insp["container_id"],
                type="vision.completed",
                payload={"zones": zones, "fresh": fresh},
            )
            conn.execute(
                "UPDATE inspections SET status = 'vision_done' WHERE inspection_id = ?",
                (inspection_id,),
            )
        finally:
            conn.close()

        await app.state.hub.broadcast({
            "type": "vision.zones",
            "inspection_id": inspection_id,
            "container_id": insp["container_id"],
            "zones": zones,
        })
        return {
            "inspection_id": inspection_id,
            "container_id": insp["container_id"],
            "status": "vision_done",
            "event_id": event["event_id"],
            "zones": zones,
            "photos": [
                {**p, "url": f"/assets/{p['file']}"}
                for p in photos
            ],
        }

    def _latest_payload(conn, inspection_id: str, event_type: str) -> dict | None:
        row = conn.execute(
            "SELECT payload_json FROM events WHERE inspection_id = ? AND type = ?"
            " ORDER BY seq DESC LIMIT 1",
            (inspection_id, event_type),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    @app.post("/v0/inspections/{inspection_id}/run-metrology")
    async def run_metrology(inspection_id: str):
        """Mock mm values + rules eval. Metrology decides measurable concerns; human signs."""
        insp = _require_inspection(inspection_id)
        ruleset = app.state.rulesets[insp["standard_name"]]

        conn = store.get_conn(app.state.db_path)
        try:
            vision_payload = _latest_payload(conn, inspection_id, "vision.completed")
            if vision_payload is None:
                raise HTTPException(409, detail={
                    "error": "vision_not_run",
                    "reason": "run-vision must produce zones before metrology",
                })

            measurements = []
            if ruleset.mode == "measured":
                seen = set()
                for zone in vision_payload["zones"]:
                    component = zone["component"]
                    if component in seen or zone["concern"] not in fusion.MEASURABLE_CONCERNS:
                        continue
                    seen.add(component)
                    matched = match_rule(ruleset, component)
                    if matched is None or matched[1].method != "metrology":
                        continue  # no rule in this profile: falls to human review at sign
                    value = metrology.measure(
                        insp["container_id"], component, app.state.assets_dir
                    )
                    if value is None:
                        continue  # no pre-recorded value: falls to human review
                    rule_name, rule = matched
                    measurements.append({
                        "component": component,
                        "rule": rule_name,
                        "measure": rule.measure,
                        "value_mm": value,
                        "limit_mm": rule.limit_mm,
                        "result": evaluate(rule, value),
                        "source": "metrology",
                    })

            event = store.append_event(
                conn,
                inspection_id=inspection_id,
                container_id=insp["container_id"],
                type="metrology.completed",
                payload={"mode": ruleset.mode, "measurements": measurements},
            )
            conn.execute(
                "UPDATE inspections SET status = 'metrology_done' WHERE inspection_id = ?",
                (inspection_id,),
            )
        finally:
            conn.close()

        await app.state.hub.broadcast({
            "type": "metrology.results",
            "inspection_id": inspection_id,
            "measurements": measurements,
        })
        return {
            "inspection_id": inspection_id,
            "container_id": insp["container_id"],
            "status": "metrology_done",
            "event_id": event["event_id"],
            "mode": ruleset.mode,
            "measurements": measurements,
        }

    @app.post("/v0/inspections/{inspection_id}/sign")
    async def sign(inspection_id: str, body: SignBody):
        """Human decision + overrides -> hash-chained record -> inspection.completed webhook.

        Every inspection ends here: the human sign-off IS the recorded decision
        (decision support, not a verdict engine).
        """
        insp = _require_inspection(inspection_id)
        ruleset = app.state.rulesets[insp["standard_name"]]

        conn = store.get_conn(app.state.db_path)
        try:
            vision_payload = _latest_payload(conn, inspection_id, "vision.completed")
            if vision_payload is None:
                raise HTTPException(409, detail={
                    "error": "vision_not_run",
                    "reason": "nothing to sign: run-vision first",
                })
            # metrology is optional by mode (Domestic-Lite has none); unmeasured
            # findings fall to the human, which is exactly the fusion precedence
            metrology_payload = _latest_payload(conn, inspection_id, "metrology.completed") or {}

            findings = fusion.reconcile(
                vision_payload["zones"],
                metrology_payload.get("measurements", []),
                [o.model_dump() for o in body.overrides],
            )
            record = InspectionRecord(
                inspection_id=inspection_id,
                container_id=insp["container_id"],
                direction=insp["direction"],
                standard=StandardRef(name=ruleset.standard, version=ruleset.version),
                status="signed",
                findings=findings,
                signed_by=body.signed_by,
                signed_at=datetime.now(timezone.utc).isoformat(),
            )
            # JSON record is the source of truth; it lives in the hash chain
            event = store.append_event(
                conn,
                inspection_id=inspection_id,
                container_id=insp["container_id"],
                type="inspection.completed",
                payload={"record": record.model_dump()},
            )
            record.prev_hash = event["prev_hash"]
            record.hash = event["hash"]
            conn.execute(
                "UPDATE inspections SET status = 'signed' WHERE inspection_id = ?",
                (inspection_id,),
            )
        finally:
            conn.close()

        # best-effort outbound webhook (localhost Yard System); never blocks the sign
        delivery = await run_in_threadpool(
            webhooks.fire, app.state.webhook_url, "inspection.completed", record.model_dump()
        )
        await app.state.hub.broadcast({
            "type": "inspection.signed",
            "inspection_id": inspection_id,
            "container_id": insp["container_id"],
            "record": record.model_dump(),
        })
        return {
            "inspection_id": inspection_id,
            "status": "signed",
            "event_id": event["event_id"],
            "record": record.model_dump(),
            "webhook": delivery,
        }

    @app.post("/v0/yard/inbox", status_code=202)
    def yard_inbox_receive(body: dict):
        """Dummy 'Yard System' (external consumer). Stores webhook deliveries for the tab."""
        app.state.yard_inbox.append(body)
        del app.state.yard_inbox[:-50]  # keep the last 50
        return {"received": True}

    @app.get("/v0/yard/inbox")
    def yard_inbox_list():
        return {"deliveries": app.state.yard_inbox}

    @app.get("/v0/inspections/{inspection_id}/report.pdf")
    def report_pdf(inspection_id: str):
        """PDF is a rendered view of the JSON record — never the source of truth."""
        _require_inspection(inspection_id)
        conn = store.get_conn(app.state.db_path)
        try:
            record = _signed_record(conn, inspection_id)
        finally:
            conn.close()
        pdf = report.render_pdf(record)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{inspection_id}.pdf"'},
        )

    @app.websocket("/v0/live")
    async def live(ws: WebSocket):
        await ws.accept()
        app.state.hub.sockets.add(ws)
        try:
            while True:
                msg = await ws.receive_text()
                await ws.send_json({"echo": msg})
        except WebSocketDisconnect:
            pass
        finally:
            app.state.hub.sockets.discard(ws)

    return app


app = create_app()
