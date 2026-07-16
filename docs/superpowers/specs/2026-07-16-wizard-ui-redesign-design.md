# Wizard UI Redesign — Autoneum-style full-screen inspection flow

Date: 2026-07-16 · Status: approved by user

## Goal

Replace the tab-based frontend of `container-inspect/` with a single full-screen,
Autoneum-inspired step wizard (reference: `Media/web-sample.png`,
https://acoustics.autoneum.com/). Dark cinematic look, cyan "LiDAR" accent,
3D container center stage. Backend untouched.

## Non-goals

- No backend/API changes. All existing `/v0/*` endpoints, hash chain, webhook,
  PDF stay as-is.
- No Three.js scene; 3D via `@google/model-viewer` only.
- No new inspection features — same flow, new presentation.

## Visual language

- Background `#050810` (near-black blue), CSS starfield particles, large glowing
  ring arc on the left (pure CSS/SVG — no WebGL beyond model-viewer).
- Accent: cyan (`#22d3ee` family) for active/glow; pass = emerald, concern = amber/red
  (unchanged semantics).
- Top-left: `container-inspect` wordmark. Top-right: MENU button → overlay
  (Yard System inbox, past inspections list).
- Top-center: `STEP N` eyebrow + Thai step title, uppercase-tracked English
  technical subtext, like the reference.
- Left edge: 5 step nodes positioned on the ring arc; states: done (solid cyan),
  active (glow), upcoming (dim). Clickable only backwards/completed.
- Thai UI text, technical words in English (existing rule).

## Center stage

- `super_low_poly_container.glb` rendered with `@google/model-viewer`
  (npm dependency, bundled locally — offline OK; satisfies the "glTF/GLB not stl"
  and offline constraints). `auto-rotate camera-controls`, transparent background.
- During LiDAR step scan: the mp4
  (`Simulate_Lidar_scan_container_202607160835.mp4`) fades in replacing the
  model, plays once (muted, `playsInline`), fades back to the model, then
  measurement results appear.

## Steps (state machine, single page)

1. **เลือกตู้ (SELECT CONTAINER)** — container options as radial labels on the
   right (Autoneum "HATCHBACK" style) from `/v0/meta` demo_containers; selects
   for direction + standard (IICL-6 / Domestic-Lite); ISO 6346 ✓ badge after
   `POST /v0/inspections`.
2. **Vision** — button runs `POST run-vision`; photos + normalized bbox overlays
   appear in a right-side panel strip beside the model (model stays center);
   persistent banner "Vision ชี้จุดที่ควรตรวจ ไม่ใช่ผู้ตัดสิน".
3. **LiDAR Scan** — button triggers `POST run-metrology` + plays the mp4 center
   stage (mockup of a real scan); after video, measured values vs limits render
   beside the model (mm, pass/concern chips, source tag).
4. **ทบทวน & เซ็น (REVIEW & SIGN)** — findings list in right panel, per-item
   override (result + note), signed-by input, sign button → `POST sign`.
   Precedence Human > Metrology > Vision preserved and displayed.
5. **บันทึก & ส่งต่อ (RECORD)** — signed record summary: hash + prev_hash,
   webhook delivery status to Yard System, "เปิด PDF" (new tab, existing
   endpoint), "ดู Yard inbox" (opens MENU overlay), "ตรวจตู้ถัดไป" resets to
   step 1.

Guards: cannot advance past a step whose API call hasn't succeeded (mirrors
existing 409 logic). Errors render as a toast/banner, never dead-end the wizard.

## Yard System

- Kept at route `/yard` (restyled to the same theme) so it can run on a second
  screen during the demo, **and** reachable as an overlay from MENU.
- Same polling of `/v0/yard/inbox` every 2 s.

## Media/assets

- Copy `Media/super_low_poly_container.glb` and
  `Media/Simulate_Lidar_scan_container_202607160835.mp4` to
  `container-inspect/assets/media/` (served by existing `/assets` static mount).
- Remove the Sketchfab iframe + attribution (no internet dependency remains).

## Code structure (frontend)

- `App.jsx` — routes: `/` = Wizard, `/yard` = YardSystem. Tab nav removed.
- `src/wizard/Wizard.jsx` — state machine (step index, inspection, vision,
  metrology, overrides, signed), renders chrome + active step.
- `src/wizard/StepArc.jsx` — ring + step nodes.
- `src/wizard/CenterStage.jsx` — model-viewer / video crossfade.
- `src/wizard/panels/*.jsx` — right-side panel per step.
- `src/wizard/MenuOverlay.jsx` — Yard inbox + past inspections.
- Old `routes/Dashboard.jsx`, `Twin.jsx`, `Report.jsx` deleted (Report's PDF
  access moves to step 5; Twin superseded by center stage).
- `useSignedInspections` hook reused by MenuOverlay.

## Risks / mitigations

- Projector legibility: high contrast, large type, chips color + text.
- Transition jank: CSS transitions only, no JS animation loops besides
  model-viewer's own.
- Video codec: mp4 (H.264) plays natively in Chrome; fallback message + skip
  button if playback errors.
- model-viewer bundle: installed via npm, no CDN.

## Verification

- All 62 backend tests still pass (frontend-only change).
- Browser walkthrough: full 5-step flow on both demo containers, override path,
  PDF opens, webhook lands in Yard overlay + `/yard` route, offline behavior
  (no external requests except none).
