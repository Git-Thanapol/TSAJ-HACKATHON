# HANDOVER 1 — Business Identification

> **Audience:** the AI build agent + team. Read this before writing any code. It defines *what we are building and why*, so every technical choice can be checked against it. Companion doc: `HANDOVER-2-tech-stack-hackathon.md`.

---

## 1. One-line definition

**A gate/pit-stop container-inspection support system that makes inspection more productive and produces a standardized, defensible, evidence-backed inspection record — as middleware other yard/terminal software plugs into via API.**

It is **decision support, not a decision maker.** It never issues a binding verdict. A human always signs the recorded decision.

---

## 2. The problem

- At a Thailand container terminal, **inspection is the yard bottleneck** on inbound and outbound flow.
- Today's inspection is **manual, slow, inconsistent, and hard to prove after the fact** (disputes about container condition come down to memory, loose photos, or a surveyor's word).
- Standards exist (IICL-6, Maersk, CIC) but in the **real world only a few countries actually enforce millimetre-level metrology**. Most inspection is human eyeballing with no structured evidence trail.

## 3. What we are NOT trying to do (explicit non-goals)

- **Not replacing humans.** The human stays in the loop and stays in charge. We increase their productivity.
- **Not a verdict engine.** We produce findings, measurements, and flags. The human decides; the client decides whether to use the box.
- **Not chasing labour-cost reduction as the headline.** (It may happen; it is not the pitch.)
- **Not solving yard management, billing, or gate ops.** We are the *inspection layer only*. Everything else consumes us via API.
- **Not claiming certified metrology accuracy** at this stage. For the hackathon we assume/pretend the measurement technology works — this is an **idea pitch**, not a metrology-validated product.

## 4. Goals (in priority order)

1. **Productivity** — move containers through inspection faster; zone attention so humans check what matters.
2. **Standard** — every inspection is run against a named, versioned ruleset, so "what was checked" is unambiguous and repeatable.
3. **Defensible / evidence-backed** — every finding carries evidence (image crop, measurement, source, human sign-off) in an immutable, tamper-evident record.

**Explicitly de-prioritised:** labour cost, full autonomy, metrology certification.

## 5. Positioning statement (say this to VCs)

> "Inspection is the yard's bottleneck. We don't replace the inspector — we make them faster and turn every inspection into a standardized, defensible, evidence-backed record. Vision points to where to look, sensors add the numbers, the human decides, and the result is a trusted record any yard or leasing system can consume through our API. Productivity that comes *with evidence* is the product."

## 6. Roles of the three input sources (LOCKED)

- **Vision (local YOLOv12):** **triage + zoning only.** Detects/localises dents, rust, tears, holes, stains and tells the human *where to look and what to be concerned about.* **Never decides.**
- **Metrology (LiDAR / photogrammetry):** provides the **number** for measurable criteria (dent depth, intrusion, step height) when a standard needs one. Assumed-working for the demo.
- **Human:** judges what no sensor can (e.g. stain "dry vs transferrable", smell), and **signs the final recorded decision.** Captured as structured, signed evidence.

**Conflict precedence for the recorded decision (LOCKED): `Human > Metrology > Vision`.**
Human overrides anything. For measurable criteria the metrology number outranks vision. Vision never outranks either — it only zones. Every finding must record **which source produced it** and whether a human overrode it.

## 7. Customers & who pays

Two buyers, one system (this is a strength, not a conflict):

| Buyer | Role | What they buy | Value to them |
|---|---|---|---|
| **Terminal / depot** | Operator **and** primary buyer | The software (+ hardware) at the gate/pit-stop | Productivity through the bottleneck; a standardized inspection process they control |
| **Leasing co / shipping line (client)** | Secondary buyer | The **inspection report / record** + API access | A defensible, standard-referenced condition record for their box |

**Key ownership fact (clarification 10):** once a container leaves the terminal it is **not the terminal's responsibility**. The **inspection report is for the client** — the client decides whether to accept/use the box. So the record must be **portable and trustworthy to a party that never touched our hardware.** That portability is what makes the second revenue stream (selling records to lessors/lines) possible.

## 8. Liability posture (LOCKED)

**Decision support, human-in-the-loop.** A human signs every recorded decision. We are a tool that improves productivity and evidence quality — we are not in the verdict/liability chain. Keep this framing in the UI (every inspection ends with a human sign-off) and in the pitch.

## 9. Moat / why this is defensible

1. **The record** — signed, tamper-evident, standard-referenced, with evidence per finding. Hard to copy, valuable to whoever disputes container condition.
2. **Standard-as-versioned-data + rules engine** — standards become configurable data, not code. New standard = new config, not a rewrite. This is more of the IP than the YOLO model.
3. **Local Thai-yard labelled dataset** — grows every time a human inspects (they label as they go). Competitors can't buy this.

## 10. Market reality to keep honest

- Standards (IICL/Maersk) are **guidelines** for us right now, not a hard requirement — because most markets don't enforce metrology. We support them as *profiles* but our near-term value is **productivity + evidence**, which applies even to appearance-only / domestic jobs.
- Therefore ship an **"appearance-only / domestic-lite" profile** as a first-class option, not an afterthought. Many customers just want fast, evidenced appearance checks.

## 11. Development phases (roadmap)

Each phase has a **goal**, a **business milestone that unlocks the next phase**, and a note on **what becomes technically real** (vs mocked). The rule of thumb: *mock everything until a paying/anchor customer forces it to be real.*

### Phase 0 — Proof of concept (Hackathon) · now
- **Goal:** prove the *workflow and the record*, not the sensors. Land the pitch narrative.
- **Scope:** end-to-end thin slice — ID → vision zoning → mocked measurement vs standard → human sign-off → hash-chained record → PDF + 3D twin + API/webhook. (Full build spec in `HANDOVER-2`.)
- **Real vs mocked:** vision (local YOLOv12) real; **metrology mocked**; data pre-recorded; single laptop.
- **Business milestone → unlocks Phase 1:** a pitch that gets a **verbal LOI / "we'd pilot this"** from one terminal or one lessor.
- **Exit criteria:** demo runs reliably in < 1 min; two-buyer story is crisp; judges/VCs understand "productivity with evidence."

### Phase 1 — Pilot at one anchor site · ~1–3 months
- **Goal:** run the system on **real containers at one terminal**, in parallel with human inspectors (shadow mode). Collect labelled data.
- **Scope:** gate/pit-stop camera install; **YOLOv12 retrained on local Thai-yard images**; rules engine with IICL-6 subset + Domestic-Lite; real hash-chained records exported to the client. **Metrology still optional/light** (photogrammetry or phone-LiDAR screening; boundary cases → human).
- **Real vs mocked:** vision real + improving from local labels; measurement = *screening only*, not certified; API consumed by the terminal's existing system.
- **Business milestone → unlocks Phase 2:** **one anchor customer accepts our record** as useful in their real process (terminal for productivity, and/or one lessor/line paying for the record). This is the single most important non-technical milestone in the whole plan.
- **Exit criteria:** measurable throughput gain vs manual; inspectors *want* to keep using it; a repeatable install playbook.

### Phase 2 — Productized MVP · ~3–9 months
- **Goal:** turn the pilot into a product two buyers pay for.
- **Scope:** multi-standard profiles as data; **record subscription + API** productized for lessors/lines; role-based access; audit/export for disputes; hardened edge deploy (rugged, offline-first, local inference). **Metrology becomes real screening** with a published repeatability/uncertainty spec (only where a customer actually enforces mm criteria).
- **Real vs mocked:** everything real for the paths customers use; still no over-claim of full-autonomy metrology.
- **Business milestone → unlocks Phase 3:** **2–3 paying terminals + at least one lessor/line on the record subscription**; unit economics show payback.
- **Exit criteria:** repeatable sales motion; support/ops model; SLA on the API.

### Phase 3 — Scale & platform · 9+ months
- **Goal:** become the **inspection layer** of the yard ecosystem.
- **Scope:** the pit-stop gains **additional sensor "topics"** (moisture, hydrocarbon/odor, chemical, thermal) as pluggable modules — this is exactly why the gate was designed as a pit-stop in Phase 0. Multi-terminal, multi-tenant; **plugin/marketplace** so other yard software builds on our API; the standardized record becomes an industry-referenceable artifact.
- **Real vs mocked:** full multi-sensor fusion; certified metrology where markets demand it.
- **Business milestone:** network effects — the record is trusted enough that lessors *request* our inspection at partner terminals, pulling new terminals in.

> **Phasing discipline:** do not build Phase 2/3 capability during Phase 0/1. Each phase is gated by a *customer* signal, not by engineering readiness. The most common failure mode for this kind of product is building sensor breadth (Phase 3) before landing the anchor customer (Phase 1).

---

## 12. Success criteria for the hackathon pitch

- Show the **end-to-end thin slice** working (ID → zoning → measurement number vs standard → human sign-off → defensible record → report + API).
- Land the narrative: *productivity with evidence*, decision-support, two buyers/one system, middleware.
- It's an **idea pitch** — the measurement tech is assumed working; the demo proves the *workflow and the record*, not sensor accuracy.
