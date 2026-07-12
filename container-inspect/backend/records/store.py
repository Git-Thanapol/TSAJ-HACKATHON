"""Append-only, hash-chained inspection event store.

Tamper evidence: each event's hash = sha256(prev_hash + canonical(event_fields)).
Chains are per container_id so a container's history is independently verifiable.
APPEND-ONLY INVARIANT: no UPDATE/DELETE on the events table, ever.
Every history entry carries its own event_id; writes are idempotent at the API
layer (idempotency table) because trucks get re-inspected and gates double-fire.
"""
import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone

GENESIS = "0" * 64

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  seq           INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id      TEXT UNIQUE NOT NULL,
  inspection_id TEXT NOT NULL,
  container_id  TEXT NOT NULL,
  type          TEXT NOT NULL,
  ts            TEXT NOT NULL,
  payload_json  TEXT NOT NULL,
  prev_hash     TEXT NOT NULL,
  hash          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_container ON events(container_id, seq);
CREATE TABLE IF NOT EXISTS inspections (
  inspection_id TEXT PRIMARY KEY,
  container_id  TEXT NOT NULL,
  direction     TEXT NOT NULL,
  standard_name TEXT NOT NULL,
  status        TEXT NOT NULL,
  created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency (
  key           TEXT PRIMARY KEY,
  inspection_id TEXT NOT NULL
);
"""

_EVENT_FIELDS = ("event_id", "inspection_id", "container_id", "type", "ts", "payload_json", "prev_hash")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def make_id(prefix: str) -> str:
    return f"{prefix}_{time.time_ns():x}{uuid.uuid4().hex[:8]}"


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _hash_event(fields: dict) -> str:
    return hashlib.sha256((fields["prev_hash"] + canonical(fields)).encode()).hexdigest()


def append_event(conn, *, inspection_id: str, container_id: str, type: str, payload: dict) -> dict:
    last = conn.execute(
        "SELECT hash FROM events WHERE container_id = ? ORDER BY seq DESC LIMIT 1",
        (container_id,),
    ).fetchone()
    fields = {
        "event_id": make_id("evt"),
        "inspection_id": inspection_id,
        "container_id": container_id,
        "type": type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload_json": canonical(payload),
        "prev_hash": last["hash"] if last else GENESIS,
    }
    event = {**fields, "hash": _hash_event(fields)}
    conn.execute(
        "INSERT INTO events (event_id, inspection_id, container_id, type, ts, payload_json, prev_hash, hash)"
        " VALUES (:event_id, :inspection_id, :container_id, :type, :ts, :payload_json, :prev_hash, :hash)",
        event,
    )
    conn.commit()
    return event


def get_history(conn, container_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT event_id, inspection_id, container_id, type, ts, payload_json, prev_hash, hash"
        " FROM events WHERE container_id = ? ORDER BY seq ASC",
        (container_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def verify_chain(events: list[dict]) -> tuple[bool, int | None]:
    prev = GENESIS
    for i, e in enumerate(events):
        fields = {k: e[k] for k in _EVENT_FIELDS}
        if e["prev_hash"] != prev or _hash_event(fields) != e["hash"]:
            return False, i
        prev = e["hash"]
    return True, None
