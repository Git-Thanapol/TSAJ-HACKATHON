# M1 Skeleton — container-inspect (Design)

**Date:** 2026-07-12
**Scope:** Milestone M1 only, per `Core Ideas\HANDOV~2.MD` §7: FastAPI up, models defined, ruleset YAML loads, SQLite append-only store with hash chain, `POST /v0/inspections` + `GET /v0/containers/{id}/history` working with real (not dummy) chain writes. Vision (M2), metrology/fusion/sign/webhook (M3), PDF/twin (M4) are stubbed, not built.
**Approved by:** user, 2026-07-12.

## Decisions (from clarification round)

| Question | Decision |
|---|---|
| Scope | M1 skeleton only |
| Location | `container-inspect/` subdirectory of TSAJ-Hackathon repo; repo gets `git init` |
| Docker | Everything in Docker: docker-compose, backend + frontend containers, source volume-mounted, hot reload (uvicorn `--reload`, Vite dev server). Runs offline after image build. |
| Assets | None yet — `assets/README.md` documents what to drop in later (photos, YOLOv12 weights, GLB, point cloud, measurements.json) |
| Storage | Raw `sqlite3`, no ORM. One append-only events table; hash over canonical JSON. |
| API surface | Full `/v0` surface now; M2/M3 endpoints return structured 501 stubs so the contract is stable for frontend + demo script. |
| Frontend | Vite + React + Tailwind shell scaffolded now with placeholder routes (Dashboard, Twin, Report, YardSystem) so compose is complete day one. |

## Layout

```
container-inspect/
├── docker-compose.yml            # backend:8000 + frontend:5173, src volume-mounted, hot reload
├── .env.example                  # ports, DB path
├── data/                         # SQLite volume (gitignored)
├── assets/README.md              # where photos/weights/GLB drop later
├── backend/
│   ├── Dockerfile                # python:3.12-slim
│   ├── requirements.txt          # fastapi uvicorn pydantic pyyaml pytest httpx
│   ├── main.py                   # FastAPI app, /v0 routes, WS /v0/live stub
│   ├── models.py                 # Ruleset, InspectionRecord, Finding + ISO 6346 check-digit validator
│   ├── orchestrator.py           # pipeline skeleton: vision → metrology → rules → fusion (stub calls)
│   ├── rules/engine.py           # YAML load + value-vs-limit eval (real, tested in M1)
│   ├── records/store.py          # append-only events + hash chain
│   ├── vision/yolo_service.py    # stub (M2)
│   ├── metrology/mock.py         # stub (M3)
│   ├── fusion.py                 # stub; precedence constant Human > Metrology > Vision (M3)
│   ├── webhooks.py               # stub (M3)
│   ├── standards/iicl6.yaml      # exact schema from HANDOV~2 §4
│   ├── standards/domestic_lite.yaml
│   └── tests/
└── frontend/
    ├── Dockerfile                # node:24-slim, Vite dev server
    └── src/                      # React Router: Dashboard | Twin | Report | YardSystem placeholders
```

## Data model

**Events table (SQLite, WAL mode):**
`event_id (ULID, PK) | inspection_id | container_id | type | ts | payload_json | prev_hash | hash`

- `hash = sha256(prev_hash + canonical_json(event_fields))`; canonical = sorted keys, no whitespace; event_fields = all columns except `hash` itself (`event_id, inspection_id, container_id, type, ts, payload_json, prev_hash`).
- Genesis `prev_hash = "0" * 64`.
- Append-only: no UPDATE/DELETE anywhere in code; chain verifier function walks the chain and detects tampering. Used by tests now, `GET /history?verify=true` later.
- Every history entry carries its `event_id`; writes take an `Idempotency-Key` header — replaying the same key returns the same inspection and appends no duplicate event.

**Pydantic models (`models.py`):** `Ruleset`, `ComponentRule`, `InspectionRecord`, `Finding`, `Measurement` — field names exactly as HANDOV~2 §4 schemas. Plus `validate_iso6346(container_id)` check-digit function (pure, tested).

## API (M1 behavior)

| Route | M1 behavior |
|---|---|
| `POST /v0/inspections` | Validate ISO 6346 check digit + standard exists → create inspection → append `inspection.started` event → return `inspection_id`. Idempotent via header. |
| `GET /v0/containers/{id}/history` | Return event list incl. hashes, oldest first. |
| `POST /v0/inspections/{id}/run-vision` | 501 `{"error":"not_implemented","milestone":"M2"}` |
| `POST /v0/inspections/{id}/run-metrology` | 501, milestone M3 |
| `POST /v0/inspections/{id}/sign` | 501, milestone M3 |
| `GET /v0/inspections/{id}/report.pdf` | 501, milestone M4 |
| `WS /v0/live` | Accepts connection, echoes ping — real pushes in M3 |

**Errors:** bad check digit → 422 with reason; unknown standard → 422 listing available profiles; unknown inspection id → 404.

## Rulesets

`standards/iicl6.yaml` and `standards/domestic_lite.yaml` verbatim per HANDOV~2 §4. `rules/engine.py` loads + validates them into `Ruleset` at startup and exposes `evaluate(component, value_mm) -> pass|concern` — real logic, tested in M1 even though nothing calls it until M3.

## Testing

pytest inside backend container: `docker compose run backend pytest`.
Cover: check digit (valid, invalid, `MSKU1234565`), both YAML profiles parse, chain append + tamper detection, POST→GET roundtrip via httpx TestClient, idempotency replay returns same inspection without duplicate event.

## Verification (definition of done)

`docker compose up` → `POST /v0/inspections` via curl → `GET /v0/containers/{id}/history` shows hash-chained event → frontend shell loads at `:5173` → all tests green in container.

## Non-goals (M1)

No YOLO, no metrology values, no fusion logic, no sign-off, no webhook firing, no PDF, no 3D twin, no WebSocket pushes. Stubs only. Do not violate locked decisions in CLAUDE.md.
