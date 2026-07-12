# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status: pre-code / planning phase

There is **no application code yet**. When you start building, create the structure described in "Planned architecture" below. This is a hackathon **thin slice** — build exactly the locked scope, favour "demo can't break on stage" over "impressive but fragile", and do not expand beyond the inspection layer.

## Repo layout — what is (and is not) the project

- **`Core Ideas\`** — the actual project: design docs + reference PDFs (see below). This is the only project-relevant content in the repo today.
- **Everything else at repo root** (`README.md`, `WORLDFLOWAI.md`, `agents/`, `commands/`, `skills/`, `rules/`, `hooks/`, `scripts/`, `tests/`, `contexts/`, `examples/`, `mcp-configs/`, `.claude-plugin/`) is a vendored copy of the **`everything-claude-code`** Claude Code plugin repo — tooling reference, **not the hackathon app**. Do not treat the root `README.md` as the project readme, do not build inside these directories, and do not "fix" or test them unless explicitly asked. `Core Ideas\CONTRIBUTING.md` also belongs to that plugin repo, not this project.

### Source-of-truth documents (read these first)

All in `Core Ideas\`. On-disk names are 8.3-truncated; content titles differ. Reference them by these exact paths in tools:

- `Core Ideas\HANDOV~1.MD` — **Handover 1: Business Identification.** *Why* we're building this: problem, non-goals, goals (productivity → standard → defensible evidence), two-buyer model (terminal pays for software; lessor/line pays for the record), phased roadmap (Phase 0 = this hackathon). Read before making any technical choice.
- `Core Ideas\HANDOV~2.MD` — **Handover 2: Tech Stack Design.** The build spec for the hackathon thin slice: stack, schemas, API surface, repo layout, build order, guardrails, and the exact on-stage demo flow (§3). **Primary implementation reference.**
- `Core Ideas\CONTAI~1.MD` — **Container Inspection Middleware: Refined System Design.** Deep design rationale and honest risk analysis behind the locked decisions (why metrology is core, why the record is the product, liability posture).
- `Core Ideas\Maersk Container Inspection Criteria (short version).pdf`, `Core Ideas\tb_013.pdf` — the real inspection standards the ruleset YAMLs are derived from (IICL-6 / Maersk, defined mostly in millimetres).

If any planned filename or design detail here conflicts with the handover docs, the handover docs win — re-read them rather than trusting this summary.

## What this is

A **gate/pit-stop container-inspection support system**: middleware that makes container inspection faster and produces a standardized, defensible, evidence-backed inspection record, exposed via API so yard/terminal software can consume it. It is **decision support, not a decision maker** — a human signs every recorded decision. Pitch framing: "productivity with evidence"; the signed record — not the YOLO model — is the product and the moat.

## Locked decisions — do not re-litigate, do not violate

These constraints drive the whole architecture and are the easiest thing to accidentally break:

- **Three input sources, fixed roles.** Vision (local YOLOv12) does **triage/zoning only — it never emits pass/fail**. Metrology (LiDAR/photogrammetry) provides the measured number; for the demo it is **mocked**, reading pre-recorded values. Human judges what no sensor can (e.g. stain "dry vs transferrable") and **signs the final decision**.
- **Conflict precedence: `Human > Metrology > Vision`.** Every finding must record which source produced it and whether a human overrode it. This lives in `fusion.py`.
- **Every inspection ends with a human sign-off.** This is the liability posture (human-in-the-loop = decision support, not a verdict engine), not an optional UI step.
- **JSON record is the source of truth; the PDF is rendered from it.** Never make the PDF authoritative.
- **History is append-only and hash-chained.** Each inspection is a new, tamper-evident event referencing the prior event's hash. Never overwrite history.
- **Standards are versioned data, not code** — YAML rulesets (component → measurement type → threshold → method). Adding a standard = new config, not a rewrite. Ship an **IICL-6 subset** profile and a **Domestic-Lite appearance-only** profile (the latter is a first-class option, not an afterthought).
- **Everything runs on one laptop, offline.** YOLO runs **locally from weights on disk** — never call a hosted/cloud inference API. The only intentional network call is the local webhook to the dummy "Yard System" tab.
- **Do not build real metrology** (mock it) and **do not expand scope** into yard management, billing, or gate hardware.

## Planned architecture

The **Rules Engine + Fusion + Record is the real product**; Vision and Metrology are swappable inputs. Orchestrator runs `vision → metrology → rules → fusion → record`. Build in a new `container-inspect/` directory (or agree a root layout with the user before scaffolding):

```
container-inspect/
├── backend/                    # Python 3.11+, FastAPI
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
│   └── standards/*.yaml        # iicl6.yaml, domestic_lite.yaml
├── frontend/                   # Vite + React + Tailwind
│   └── src/routes: Dashboard, Twin, Report, YardSystem
└── assets/                     # pre-recorded photos, GLB, point cloud, measurements.json
```

**Stack:** FastAPI + uvicorn (REST + WebSocket), `ultralytics` (YOLOv12, local weights), `pydantic`, `pyyaml`, `sqlmodel`/`sqlite3`, `reportlab`/`weasyprint` (PDF from JSON), `hashlib` (hash chain). Frontend: React + Vite + Tailwind; 3D twin via `@google/model-viewer` (glTF/GLB) — **use glTF/GLB, not .stl**; keep the raw point cloud (LAS/LAZ/PLY) as measurement ground truth.

### API surface (v0 — namespaced `/v0/`)

- `POST /v0/inspections` — start (container_id, direction, standard) → inspection_id
- `POST /v0/inspections/{id}/run-vision` — YOLO zoning on cached images
- `POST /v0/inspections/{id}/run-metrology` — mock mm values + rules eval
- `POST /v0/inspections/{id}/sign` — human decision + overrides → writes hash-chained record → fires `inspection.completed` webhook
- `GET /v0/containers/{id}/history` — append-only event list
- `GET /v0/inspections/{id}/report.pdf` — rendered PDF
- `WS /v0/live` — push dashboard updates
- Outbound webhook `inspection.completed` → the Yard System tab

Put **idempotency keys on writes** and an **event id on every history entry** (trucks get re-inspected, gates double-fire) — this demonstrates the middleware thesis.

See `Core Ideas\HANDOV~2.MD` §4 for the exact `Ruleset` and `InspectionRecord` schemas — implement them as written. Container IDs are ISO 6346 with **check-digit validation** shown in the demo.

## Build order

M1 skeleton (FastAPI, models, YAML load, SQLite + hash chain) → M2 vision (local YOLOv12 → zones → dashboard overlays) → M3 rules + mock metrology + fusion + sign-off + webhook → M4 outputs (PDF, 3D twin, Yard System tab) → M5 polish (two inspections of one box so history grows, Domestic-Lite toggle, timing, fallbacks). The exact stage demo flow is `Core Ideas\HANDOV~2.MD` §3 — rehearse against it. Target: the whole slice runs visibly in **under a minute**.

## Commands

No build/lint/test tooling exists yet for the project — scaffold it when you create the backend/frontend. Expected once built:

- Backend: `uvicorn backend.main:app --reload` (from `container-inspect/`, venv with the deps above).
- Frontend: `npm run dev` (Vite) inside `frontend/`.

(`node tests/run-all.js` at repo root tests the vendored plugin, not this project.)

## Environment notes

- Windows 11; the primary shell here is **PowerShell** (a Bash tool is also available for POSIX scripts). Watch for CRLF and path-separator issues in any tooling you add.
- The design docs live in `Core Ideas\` with 8.3-truncated names (`HANDOV~1.MD`, etc.) — reference them by those exact paths in tools; the folder name contains a space, so quote paths.
