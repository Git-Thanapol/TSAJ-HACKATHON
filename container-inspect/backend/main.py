import json
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from models import validate_iso6346
from records import store
from rules.engine import load_rulesets

VERSION = "0.1.0"


class StartInspection(BaseModel):
    container_id: str
    direction: Literal["inbound", "outbound"]
    standard: str


def create_app(db_path: str | None = None, standards_dir: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("DB_PATH", "/data/inspections.db")
    standards_dir = standards_dir or os.path.join(os.path.dirname(__file__), "standards")

    app = FastAPI(title="container-inspect", version=VERSION)
    app.state.db_path = db_path
    app.state.rulesets = load_rulesets(standards_dir)

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
            conn.commit()
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

    return app


app = create_app()
