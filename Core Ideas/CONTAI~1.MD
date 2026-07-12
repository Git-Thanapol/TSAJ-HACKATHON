# Container Inspection Middleware — Refined System Design

**Author:** Kidprasert · **Reviewer notes by:** logistics / systems design pass
**Status:** Hackathon kickoff → seed pitch
**Context:** Thailand container terminal. Inspection is the yard bottleneck on inbound/outbound. Goal: increase **reliability, productivity, traceability**; reduce **inspection operating cost**. Integrate sensors + human. Ship as **middleware** with an inspection API that yard/depot software plugs into.

**Decisions locked for this version**
- Hackathon deliverable = **end-to-end thin slice** (ID → appearance AI → pass/fail vs one standard → report).
- Primary buyer for the VC story = **leasing companies / shipping lines** (owners of the equipment and the standards).

---

## 0. The one reframe that changes the whole design

Read your two standards carefully. Both **Maersk** and **IICL-6** define pass/fail almost entirely in **millimetres**:

- Dent on panel: internal width change **≤ 50 mm** (Maersk); side/front panel **≤ 35 mm internal cube intrusion** (IICL-6).
- Gouge on floor: **≤ 15 mm** depth, or 6–15 mm depth over **≤ 150 mm** width.
- Corner posts: **≤ 20 mm**, any number of dents (IICL-6).
- Roof: **≤ 40 mm** internal cube intrusion. Flooring height difference **≤ 5 mm**.
- Oil / rust / strange stain: acceptance = **"dry and non-transferrable"** (a tactile/chemical property, not a visual one).

**Implication that must drive the architecture:**

1. **A camera + YOLO cannot pass/fail these standards.** YOLO tells you *"there is a dent here"* (detection/classification). The standard asks *"is the dent ≤ 35 mm?"* (metrology). Those are different problems. Vision does **triage and localisation**; **measurement** decides accept/reject. This is exactly why your LiDAR idea is not a "nice-to-have optional feature" — for any standards-grade verdict, **metrology is the core, not the killer add-on.**
2. **"Dry and non-transferrable" is not measurable by camera or LiDAR at all.** No optical sensor tells you whether a stain rubs off. This criterion is inherently **human or contact-sensor** (wipe test / moisture / hydrocarbon sensor). Your design must formally accept that **some criteria will always be human-attested**, and your value is making that attestation *traceable and structured*, not eliminating it.

So the honest positioning is: **YOLO = fast triage + defect localisation; metrology (LiDAR/photogrammetry) = the number that meets the standard; human = the criteria no sensor can judge, captured as structured, signed evidence.** Reliability comes from **fusing and reconciling** these three, plus recording *which* source produced each verdict.

---

## 1. Refined end-to-end pipeline

Your 12 steps, tightened, reordered, and with the failure-handling that a real yard needs.

### 1.1 Identify (your step 1)
- OCR/read container ID (ISO 6346) **and validate the check digit** — this is free and instantly rejects mis-reads. Also read the ISO size/type code (e.g. 22G1) so the system knows the container geometry it's about to measure against.
- Capture the BIC/owner prefix → this tells you *which standard likely applies* before the operator even chooses.
- **Design for OCR failure.** Rain, mud, repaint, damaged markings. Fallback = OR-code/RFID gate tag, or manual entry. Never let a bad ID silently attach to the wrong history record — a wrong ID poisons traceability worse than no ID.
- **Deep question:** is the ID read at a **gate/OCR portal** the truck drives through, or at a **static inspection bay**? These are different capex, throughput, and integration stories. For leasing-co buyers, gate-level "on/off-hire" events are the moment they care about.

### 1.2 Select standard (your step 2)
Good instinct. Refine into a **rules engine**, not a hard-coded switch:
- A standard = a **versioned, machine-readable ruleset** (JSON/YAML): component → measurement type → threshold → measurement method. IICL-6 vs IICL-5 vs CIC vs Maersk vs your "Domestic-Lite" all become **data**, not code. (I've sketched this in §4.)
- Standards **change** (IICL-5 → IICL-6 was a dated cutover). Version and date-stamp every ruleset so a report is reproducible: "evaluated against IICL-6 rev 2016-08-01."
- Your "custom/domestic appearance-only" idea is correct and commercially smart — but make it a *named, versioned profile* too, so a customer can't later dispute "what did 'appearance check' actually mean that day?"

### 1.3–1.5 Sense
- **Appearance (YOLO):** dent, tear, wear, rust, hole, stain **localisation**. Output = defect type + bounding box/mask + which panel + confidence. Treats this as *"where to look and what kind,"* feeding measurement — not as the verdict.
  - *Roboflow-hosted vs local:* for a yard, **local/edge inference is almost mandatory** (latency, connectivity, and you don't want to ship every container's imagery to a third-party cloud for lessor-confidential equipment). Use Roboflow to *train/version* the dataset; **deploy the weights locally.** Decide this early — it affects your whole data pipeline.
  - YOLOv12: fine for a hackathon. But your moat is **not** the model — it's the labelled Thai-yard dataset and the standards mapping. Say that to VCs.
- **Metrology (LiDAR / photogrammetry):** the measurement that meets the standard. See §3 for the hard truths about accuracy.
- **Contact/other sensors:** moisture, hydrocarbon/VOC ("odor"/oil), maybe a simple wipe-transfer test rig. Gate these behind the selected standard so you don't pay for sensors a job doesn't need.

### 1.6–1.7 Fuse + evaluate (your steps 6, 7, 10)
- **Sensor fusion is where the product actually lives.** Concretely: YOLO says "dent, left panel, 0.82"; LiDAR returns "max intrusion 41 mm at that mask"; ruleset says "IICL-6 side panel limit 35 mm" → **verdict = REJECT, reason = 41 > 35 mm, evidence = [image crop, point-cloud slice, measurement method].**
- **Every verdict must carry: value, threshold, method, source, confidence, and a human-override flag.** This is the difference between "an AI said fail" and "a defensible, auditable inspection record" — which is exactly what a leasing company will pay for (they live and die on repair-cost disputes).
- **Conflict policy:** what happens when YOLO sees a defect but LiDAR measures it as in-tolerance, or vice-versa? Define precedence rules *now* (metrology > vision for measurable criteria; human > all for attested criteria). Undefined conflict handling is the #1 way "multi-sensor fusion" becomes mush.

### 1.8–1.9 Record + report (your steps 8, 9)
- Append to **immutable container-ID history** (see traceability, §5). Each inspection = an event, never overwritten.
- Report artefacts: **PDF** (the human/legal document) + **3D twin link** (.stl/.glb + point cloud) + **structured JSON** (for machines / the API). Don't make PDF the source of truth — make the JSON the source of truth and *render* the PDF from it.
- **.stl is the wrong 3D format** for a digital twin with inspection metadata — it stores raw triangles, no colour, no texture, no annotations, no measurements. Use **glTF/GLB** (web + mobile native, textures, annotations) and keep the raw **point cloud (LAS/LAZ or PLY)** as the measurement ground truth. Serve glTF to customers; keep the point cloud for audit/dispute.

### 1.10–1.12 Middleware + API (your steps 10, 11, 12)
Your "be the inspection layer, let other software consume it" thesis is the right scope discipline. Refine:
- Ship a **clean inspection API** (§4) + **webhooks** ("inspection.completed", "container.rejected") so a TOS/yard system reacts in real time.
- Offer both **push** (webhook) and **pull** (REST/GraphQL). Yard systems are legacy; some can only poll.
- **Idempotency + event IDs** everywhere — trucks get re-inspected, networks drop, gates double-fire.

---

## 2. Refined architecture (thin-slice-friendly)

```
                    ┌─────────────────────────────────────────────┐
  Inbound/Outbound  │                 INSPECTION EDGE              │
   container  ─────▶ │  ID/OCR  │  Cameras+YOLO  │ LiDAR │ sensors  │
                    └───────┬───────────┬────────────┬─────┬───────┘
                            │           │            │     │
                            ▼           ▼            ▼     ▼
                    ┌─────────────────────────────────────────────┐
                    │        FUSION + RULES ENGINE (core)          │
                    │  normalize → measure → evaluate vs ruleset   │
                    │  reconcile conflicts → verdict + evidence    │
                    └───────┬─────────────────────────┬───────────┘
                            │                          │
                 ┌──────────▼─────────┐      ┌─────────▼──────────┐
                 │  Container History  │      │   Report Service   │
                 │  (immutable events) │      │ PDF · glTF · JSON  │
                 └──────────┬─────────┘      └─────────┬──────────┘
                            │                          │
                    ┌───────▼──────────────────────────▼───────────┐
                    │   INSPECTION API  (REST/GraphQL + webhooks)   │
                    │   consumed by TOS / yard / lessor systems     │
                    └───────────────────────────────────────────────┘
```

**Why this shape:** the **rules engine is the product**. Sensors are swappable inputs; consumers are swappable outputs; the defensible middle — "measured X, standard said Y, here's the signed evidence" — is what you own and what's hard to copy.

---

## 3. Technical limitations & crises (be honest with VCs about these)

**LiDAR / metrology accuracy — your biggest technical risk.**
The standards demand **±few-mm** verdicts (5 mm flooring height; 20 mm corner-post limit). Delivering that reliably is *hard*:
- Cheap solid-state / spinning LiDAR (Livox, RealSense-class) is typically **cm-level**, not mm-level, at container standoff distances. You may be unable to distinguish a 33 mm (pass) from a 37 mm (fail) dent — precisely the boundary that matters.
- **Registration/alignment error** (stitching multiple scans into one hull) compounds into the measurement. "Internal cube intrusion" requires a clean reference plane — a deformed container gives you no trustworthy reference to measure against.
- Reflective/wet/dark steel, sunlight, and a **moving throughput environment** all degrade point clouds.
- **Mitigation to state:** (a) use metrology to *screen* — auto-pass the obvious, auto-fail the obvious, and **route the boundary cases to a human**; don't claim full autonomy. (b) Consider **structured-light or photogrammetry** for the interior where you can control lighting. (c) Publish a measured **accuracy/repeatability spec** — a serious lessor will ask "what's your measurement uncertainty?" and "no answer" loses the deal.

**Throughput vs the bottleneck you're trying to fix.** A full LiDAR interior+exterior scan + fusion can take minutes per box. If that's slower than the human it replaces, you've **moved the bottleneck, not removed it.** Define a target **cycle time** and design to it. The thin slice should time itself.

**YOLO limitations.** Detects, doesn't measure; struggles with rust *severity* vs surface stain, hairline cracks, and anything needing scale. Needs a **known scale reference** or paired depth to convert pixels→mm. Domain shift (your Thai yard ≠ Roboflow public data) will hurt until you have local labels.

**"Non-transferrable" and smell/chemical criteria** — no camera solves these. Accept human/contact capture; don't over-promise automation here.

**Edge compute + connectivity.** GPU at the edge, weatherproofing (IP65+), calibration drift, power. Yards are hostile (dust, heat, vibration, forklifts). Ruggedisation is a real cost line, not a footnote.

**Calibration & drift** — multi-sensor fusion is only as good as extrinsic calibration between camera and LiDAR. It drifts. You need a routine (and a documented procedure) or measurements silently rot.

---

## 4. Data model & API sketch (makes you *middleware*, not a demo)

**Ruleset (standard-as-data) — the heart of "select standard":**
```yaml
standard: IICL-6
version: 2016-08-01
components:
  side_panel:
    measure: internal_cube_intrusion   # mm
    limit: 35
    method: lidar|photogrammetry
  corner_post:
    measure: max_dent
    limit: 20
    any_number_of_dents: true
  floor_height_diff:
    measure: step_height
    limit: 5
  floor_gouge:
    measure: depth
    limit: 15
    method: lidar
  oil_stain:
    measure: transferable          # boolean
    accept_if: false
    method: human|wipe_sensor      # NOT vision
```

**Inspection record (source of truth; PDF is rendered from this):**
```json
{
  "inspection_id": "insp_01H...",
  "container_id": "MSKU1234565",       // ISO 6346, check-digit validated
  "iso_type": "22G1",
  "direction": "inbound",
  "standard": {"name": "IICL-6", "version": "2016-08-01"},
  "verdict": "REJECT",
  "findings": [
    {"component":"side_panel_left","defect":"dent",
     "value_mm":41,"limit_mm":35,"result":"fail",
     "source":"lidar","confidence":0.91,
     "evidence":["img/crop_12.jpg","cloud/slice_12.laz"],
     "human_override":null}
  ],
  "twin": {"gltf":"...glb", "pointcloud":"...laz"},
  "operator": "user:117", "signed_at": "2026-07-11T09:14:00+07:00"
}
```

**API surface (v0):** `POST /inspections` (start), `POST /inspections/{id}/findings`, `GET /containers/{id}/history`, `GET /inspections/{id}/report.pdf`, webhooks `inspection.completed` / `container.rejected`. Version it (`/v0/`). Idempotency keys on writes.

---

## 5. Traceability — make it a moat, not a checkbox

Leasing companies pay for **defensible history** (on-hire/off-hire condition = who pays for which damage). So:
- **Append-only, hash-chained event log** per container ID (each event references the prior event's hash). You don't need a blockchain; a signed hash chain gives tamper-evidence a lessor's auditor will accept.
- Store **evidence** (image crops, point-cloud slices) with each verdict, immutably. In a repair-cost dispute, the party with signed, timestamped, standard-referenced evidence wins. **That is the product.**
- Sign operator attestations (the human criteria) so "dry/non-transferrable = pass" has a name and time attached.

---

## 6. Business limitations & crises (the part that decides funding)

**Crisis #1 — two buyers, one system (resolved in your favour — but design for both).** Decision update: **the terminal operates AND buys the software**, and you also sell the trusted record to **lessors / lines**. This is the *strong* version of the model — the operator and a payer are the same party, so there's no "who funds the capex" standoff. But it means you now have **two customers with different value props from one product**, and you must serve both or the second revenue stream never appears:
- **Terminal (operator + primary buyer):** value = **throughput + labour cost reduction + a standard, defensible record they control.** They pay for the software/hardware and the operational win. This is your beachhead — sell here first, land the install, prove cycle-time.
- **Lessor / line (secondary buyer):** value = **dispute-proof, standard-referenced condition history** at on-hire/off-hire. They pay per inspection / subscription **for the record and API access**, not for hardware.
- **Design consequence:** the terminal must be able to run inspections *without* a lessor in the loop (domestic, appearance-only jobs), while the record must be *exportable and trustworthy enough* that a lessor will pay for it separately. Keep the **record portable and standards-referenced** so it has value to a party who never touches your hardware. That dual-sidedness — one operator, two payers — is a **stronger** pitch than a single-buyer story; say it that way to VCs: *"the terminal pays us to fix their bottleneck; the lessor pays us for the trust the same system produces as a byproduct."*
- **Still probe:** do terminals in Thailand actually bear the inspection labour cost, or do they bill it back to the line already? If it's already billed back, your terminal ROI story shifts from "save labour" to "charge the same, spend less, keep the margin" — a *better* pitch, but a different one.

**Crisis #2 — you're entering a regulated, incumbent trust market.** IICL-6 is a *human-surveyor* institution. Surveyors, EDI condition reports (already exists as a standard), and lessor-approved repair vendors are entrenched. "An AI says fail" carries **no contractual weight** unless a standards body / major lessor blesses it. **Your real go-to-market = get ONE lessor or line to accept your record as equivalent to a surveyor's.** Without that anchor customer, the tech is a science project. Name that as your #1 non-technical milestone.

**Crisis #3 — liability.** If your system passes a container that later fails at sea (a hole you missed → wet cargo claim), who's liable? You're now in the causal chain of an insurance claim. Decide early: are you **decision support** (human signs, you're a tool) or **system of record** (you're liable)? For seed stage, **stay decision-support** — human-in-the-loop is a feature *and* a liability shield.

**Crisis #4 — capex & unit economics.** LiDAR + GPU edge + rugged enclosure per lane is real money. Your per-inspection price must beat a surveyor's marginal cost *and* pay back hardware. Build a one-line model: `(surveyor_cost_per_box − your_cost_per_box) × boxes/day × lanes` vs `hardware capex + opex`. If you can't show payback inside ~12–18 months, terminals won't install.

**Crisis #5 — data cold-start & confidentiality.** Your accuracy needs local labelled data, but you need customers to get data, but customers need accuracy to sign. Break the loop: start **human-in-the-loop from day one** (humans label as they inspect → free training data → model improves → autonomy grows). Also: equipment imagery is lessor-confidential — a **local/edge, no-third-party-cloud** story is a sales asset, so commit to it (reinforces the "deploy weights locally, not Roboflow-hosted" call in §1.3).

**Scope creep** — moisture, odor, chemical, oil, digital twin, multi-standard, API, plugins. Every sensor is a hardware + calibration + failure mode. For seed, **appearance + one measured criterion + one standard + traceable record** is a company. The rest is roadmap.

---

## 7. Hackathon thin slice (what to actually build on stage)

Locked scope = end-to-end, shallow. Cut to this and it'll *work* and *demo*:

1. **ID:** OCR one container number **+ check-digit validation** (or accept manual entry as fallback — show you thought about failure).
2. **Standard:** load **one** ruleset from YAML (do IICL-6 side-panel + one floor criterion, plus a "Domestic-Lite appearance-only" profile to show configurability).
3. **Appearance:** YOLO detects dent/rust/hole on a few real photos → localises defect.
4. **Measurement (the honest bit):** for the demo, derive a mm value from a **single depth source or a scale-referenced photo**; if no LiDAR on hand, *simulate* the measurement from a phone-LiDAR/RealSense or a pre-captured scan — and **say it's the metrology stub.** Show the pass/fail *number vs threshold*, because that's the insight judges/VCs remember.
5. **Fusion + verdict:** produce the structured JSON record with value/threshold/method/source/confidence + human-override button.
6. **Traceability:** append to a hash-chained history for that container ID; show a second inspection of the same box and the growing history.
7. **Report:** render **PDF from the JSON** + a viewable 3D (glTF in browser) if you have a scan; link, don't attach.
8. **API:** expose `GET /containers/{id}/history` and fire an `inspection.completed` webhook to a dummy "yard system" tab — this *shows the middleware thesis* in 10 seconds.

**Demo narrative for VCs (say this):** "Vision finds it, metrology measures it against the *actual* lessor standard, the human decides the edge cases, and every verdict becomes a signed, disputable-proof record that a leasing company can trust — and any yard software can consume through our API."

---

## 8. Deep questions to resolve before the pitch

1. **Where does inspection physically happen** — drive-through gate portal or static bay? (Decides throughput, capex, integration.)
2. **What measurement uncertainty can you actually achieve**, and is it inside the standards' mm thresholds? (Run one repeatability test — measure the same dent 20×.)
3. **Who installs and who pays** — terminal operates, lessor subscribes? Nail the two-sided model.
4. **Who is your one anchor customer** that will accept your record as surveyor-equivalent? Without it, what's plan B?
5. **Decision-support or system-of-record?** (Liability posture; keep it decision-support for now.)
6. **Cycle-time budget per container** — are you faster than the human you replace?
7. **Local/edge vs cloud inference** — commit, given lessor confidentiality.
8. **Which single measured criterion** best demos "vision can't do this, we can"? (Corner-post 20 mm or floor 5 mm step are crisp, high-value picks.)

---

## 9. Verdict on your design

Strong instincts, three corrections that matter:
- **Metrology is the core, not an optional killer feature** — because the standards are numeric. Reposition LiDAR/measurement from "premium add-on" to "the thing that makes any verdict standards-valid."
- **Standard-as-versioned-data + a rules engine** is your real IP and your moat, more than the YOLO model.
- **The record — signed, hash-chained, standard-referenced, human-attested where sensors can't judge — is what a leasing company buys.** Traceability isn't step 8; it's the product.

Biggest *business* risk to answer on day one: the **terminal operates it but the lessor pays for it** split. Biggest *technical* risk: **mm-level measurement in a hostile, high-throughput yard.** Neither is fatal; both must be named out loud in the pitch, with a mitigation, or a sharp VC will name them for you.
```
