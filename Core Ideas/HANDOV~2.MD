# HANDOVER 2 — Tech Stack Design (Hackathon Demo)

> **Audience:** the AI build agent. This is a build spec for the **hackathon thin slice**. Read `HANDOVER-1-business-identification.md` first for the "why". Build exactly this scope — no more. When in doubt, favour "demo can't break on stage" over "impressive but fragile".

---

## 0. Locked decisions (do not re-litigate)

| Decision | Value |
|---|---|
| Positioning | Decision **support**, not verdict. Human signs every decision. |
| Vision role | Local **YOLOv12**, **zoning/triage only**, never decides. |
| Conflict precedence | **Human > Metrology > Vision** (record the source of every finding). |
| Sensor data (demo) | **Pre-recorded / mocked.** No live hardware dependency on stage. |
| Stack | **Python (FastAPI) backend + React web frontend.** |
| Demo surfaces | **Web dashboard + PDF report + 3D twin viewer + API/webhook demo** (all four). |
| Inspection point | **Gate / pit-stop** — designed to add more sensor "topics" later. |
| Standards | Configurable **ruleset-as-data**; ship IICL-6 subset + a **Domestic-Lite appearance-only** profile. |
| Metrology | **Assumed working / mocked.** Do not attempt real mm-accurate measurement. |

---

## 1. Architecture (demo)

```
 [ Pre-recorded assets ]        React Web App  (Vite + Tailwind)
  photos / point cloud /        ┌───────────────────────────────────────┐
  glTF / measurements           │ Dashboard │ 3D Twin │ Report │ API log │
        │                       └───────────────┬───────────────────────┘
        │                                       │  REST + WebSocket
        ▼                                       ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │                     FastAPI backend (Python)                          │
 │                                                                        │
 │  /inspections  ── Orchestrator ──┐                                     │
 │                                  │                                     │
 │   ┌────────────┐  ┌────────────┐ │ ┌────────────┐  ┌────────────────┐  │
 │   │ Vision svc │  │ Metrology  │ │ │ Rules      │  │ Report svc     │  │
 │   │ YOLOv12    │  │ svc (mock) │ │ │ engine     │  │ PDF + glTF ref │  │
 │   │ zones only │  │ returns mm │ │ │ ruleset ymls│ │                │  │
 │   └────────────┘  └────────────┘ │ └────────────┘  └────────────────┘  │
 │                                  ▼                                     │
 │            Fusion+Reconcile (Human>Metrology>Vision)                   │
 │                                  │                                     │
 │        Append-only history (SQLite) + hash chain + webhooks           │
 └──────────────────────────────────────────────────────────────────────┘
                                    │ webhook: inspection.completed
                                    ▼
                     [ Dummy "Yard System" tab ] (consumes API)
```

**Principle:** the **Rules Engine + Fusion + Record** is the real product. Vision/Metrology are swappable inputs; for the demo Metrology is a mock that reads pre-recorded values.

---

## 2. Stack & libraries

**Backend — Python 3.11+, FastAPI**
- `fastapi`, `uvicorn` — API + WebSocket for live dashboard updates.
- `ultralytics` (YOLOv12) — **run locally**, load weights from disk. Inference on pre-recorded images. Never call a hosted API.
- `pydantic` — models for Ruleset + InspectionRecord (schemas in §4).
- `pyyaml` — load standards as data.
- `sqlite3` / `sqlmodel` — append-only inspection history (single file DB; zero setup).
- `reportlab` or `weasyprint` — render PDF **from the JSON record** (JSON is source of truth; PDF is a view).
- `hashlib` — hash-chain each history event (tamper-evidence).

**Frontend — React + Vite + Tailwind**
- Dashboard, findings list with zone overlays, human sign-off button, container history.
- **3D twin viewer:** `@google/model-viewer` (drop-in web component for glTF/GLB — easiest) or `three.js` if annotations need custom control. Load a **pre-made GLB** with finding markers.
- **API/webhook demo:** a second route/tab "Yard System (external)" that subscribes to the webhook / polls `GET /containers/{id}/history` and shows the event arriving live.

**Assets (pre-recorded, prepared before the demo)**
- 5–10 real container photos (with visible dent/rust/hole) → run through YOLO once, cache the detections.
- 1 container **GLB** model + 1 **point-cloud** file (can be a public sample) for the twin.
- A small JSON of "measurements" the mock Metrology service returns per finding.

---

## 3. The demo flow (what runs on stage, step by step)

1. **Start inspection** — operator picks container ID (dropdown of pre-recorded boxes) + **direction** (inbound/outbound) + **standard profile** (IICL-6 subset **or** Domestic-Lite). → `POST /inspections`.
2. **ID confirmed** — show ISO 6346 number + **check-digit validation** passing. (Pit-stop framing: "read at the gate.")
3. **Vision zoning** — YOLO runs on the cached photos; dashboard highlights **zones of concern** ("dent — left panel", "rust — door"). Label clearly: *"Vision flags where to look. It does not decide."*
4. **Metrology (mock)** — for each measurable zone, mock service returns a mm value; rules engine compares to the profile's threshold and marks **pass / concern**. Show `value vs limit`.
5. **Human sign-off** — operator reviews flags, can **override** any finding, then **signs**. This is the moment that produces the recorded decision. Precedence `Human > Metrology > Vision` visible in the record.
6. **Record written** — appended to hash-chained history. Run a **second inspection of the same box** to show the history growing (traceability).
7. **Outputs** — open the **3D twin** (annotated findings), **generate the PDF report** ("report is for the client"), and show the **Yard System tab** receiving the `inspection.completed` webhook live.

**Timing target:** the whole slice should visibly run in well under a minute (productivity story).

---

## 4. Core schemas (implement these exactly)

**Ruleset — `standards/iicl6.yaml` (subset) and `standards/domestic_lite.yaml`:**
```yaml
standard: IICL-6
version: "2016-08-01"
mode: measured            # measured | appearance_only
components:
  side_panel:   { measure: internal_cube_intrusion, limit_mm: 35, method: metrology }
  corner_post:  { measure: max_dent,                limit_mm: 20, method: metrology, any_number_of_dents: true }
  floor_height: { measure: step_height,             limit_mm: 5,  method: metrology }
  oil_stain:    { measure: transferable,            accept_if: false, method: human }   # NOT vision
```
```yaml
standard: Domestic-Lite
version: "2026-01"
mode: appearance_only     # vision zones + human sign-off, no mm thresholds
components:
  appearance: { measure: human_review, method: human, zones_from: vision }
```

**Inspection record (JSON = source of truth; PDF rendered from it):**
```json
{
  "inspection_id": "insp_01H...",
  "container_id": "MSKU1234565",
  "iso_type": "22G1",
  "direction": "inbound",
  "standard": { "name": "IICL-6", "version": "2016-08-01" },
  "status": "signed",
  "findings": [
    {
      "component": "side_panel_left",
      "concern": "dent",
      "zone_source": "vision",            // YOLO flagged the zone
      "measurement": { "value_mm": 41, "limit_mm": 35, "source": "metrology", "result": "concern" },
      "decision_source": "human",         // precedence: Human > Metrology > Vision
      "human_override": false,
      "evidence": ["img/crop_12.jpg", "cloud/slice_12.laz"]
    }
  ],
  "twin": { "gltf": "boxes/MSKU1234565.glb", "pointcloud": "boxes/MSKU1234565.laz" },
  "signed_by": "user:117",
  "signed_at": "2026-07-11T09:14:00+07:00",
  "prev_hash": "0xabc...", "hash": "0xdef..."     // hash chain
}
```

## 5. API surface (v0 — build these)

- `POST /v0/inspections` → start (container_id, direction, standard) → returns inspection_id.
- `POST /v0/inspections/{id}/run-vision` → YOLO zoning on cached images.
- `POST /v0/inspections/{id}/run-metrology` → mock mm values + rules eval.
- `POST /v0/inspections/{id}/sign` → human decision + overrides → writes hash-chained record → **fires webhook** `inspection.completed`.
- `GET /v0/containers/{id}/history` → append-only event list (traceability).
- `GET /v0/inspections/{id}/report.pdf` → rendered PDF.
- `WS /v0/live` → push dashboard updates.
- Webhook out: `POST {subscriber_url}` with `inspection.completed` (the Yard System tab subscribes).

Add **idempotency keys** on writes and an **event id** on every history entry — mention in code comments even if lightly enforced (shows the agent understood the middleware thesis).

## 6. Repo structure

```
container-inspect/
├── backend/
│   ├── main.py                 # FastAPI app + routes
│   ├── orchestrator.py         # runs vision → metrology → rules → fusion
│   ├── vision/yolo_service.py  # local YOLOv12, zoning only
│   ├── metrology/mock.py       # returns pre-recorded mm values
│   ├── rules/engine.py         # load yaml, evaluate value vs limit
│   ├── fusion.py               # Human > Metrology > Vision reconcile
│   ├── records/store.py        # SQLite append-only + hash chain
│   ├── records/report.py       # JSON -> PDF
│   ├── models.py               # pydantic: Ruleset, InspectionRecord, Finding
│   ├── webhooks.py
│   └── standards/*.yaml
├── frontend/                   # Vite + React + Tailwind
│   └── src/routes: Dashboard, Twin, Report, YardSystem
├── assets/                     # pre-recorded photos, GLB, point cloud, measurements.json
└── README.md
```

## 7. Build order (milestones for the agent)

1. **M1 — Skeleton:** FastAPI up, models defined, ruleset YAML loads, SQLite store with hash chain. `POST /inspections` + `GET history` work with dummy data.
2. **M2 — Vision:** local YOLOv12 loads weights, runs on cached photos, returns zones. Dashboard shows zone overlays.
3. **M3 — Rules + mock metrology + fusion:** value-vs-limit eval; fusion applies `Human > Metrology > Vision`; sign-off endpoint writes the record + fires webhook.
4. **M4 — Outputs:** PDF from JSON; 3D twin viewer loads GLB with markers; Yard System tab consumes the webhook.
5. **M5 — Polish + demo script:** two inspections of one box (history grows), Domestic-Lite profile toggle, timing, fallbacks. **Rehearse the exact stage flow in §3.**

## 8. Guardrails for the agent (avoid these traps)

- **Do NOT** call any hosted/cloud inference API — YOLO runs local, on disk.
- **Do NOT** build real metrology/point-cloud measurement — it's a mock reading pre-recorded values.
- **Do NOT** let vision output a pass/fail — vision only produces zones/concerns.
- **Do NOT** make PDF the source of truth — render it from the JSON record.
- **Do NOT** overwrite history — every inspection is a new, hash-linked event.
- **Do NOT** expand scope beyond inspection (no yard mgmt, billing, gate hardware).
- **Every inspection MUST end with a human sign-off** — this is the decision-support/liability posture, not optional.
- Keep everything runnable on **one laptop, offline** (except the intentional webhook to the local Yard System tab).
