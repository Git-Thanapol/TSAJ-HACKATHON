"""Conflict reconciliation. LOCKED precedence: Human > Metrology > Vision.

Every finding records which source produced it and whether a human overrode it.
Vision only proposes zones (it never decides); metrology's measured result
supersedes vision's concern; a human override supersedes everything and every
inspection ends with a human signing the reconciled findings.
"""

PRECEDENCE = ("human", "metrology", "vision")  # highest first

# Concerns a mm measurement can decide (deformation). Rust/stains are
# appearance judgements — no number settles them, so they fall to the human.
MEASURABLE_CONCERNS = {"dent", "hole"}


def reconcile(zones: list[dict], measurements: list[dict], overrides: list[dict]) -> list[dict]:
    """Merge vision zones + metrology measurements + human overrides into findings.

    zones:        [{image, component, concern, bbox, confidence, source}]
    measurements: [{component, measure, value_mm, limit_mm, result, source}]
    overrides:    [{component, concern, result, note?}] — human decisions at sign-off

    Returns Finding-shaped dicts. decision_source = highest precedence source
    that determined the final result; human_override marks an explicit human
    change. One finding per (component, concern); zone images become evidence.
    """
    by_component = {m["component"]: m for m in measurements}
    override_key = {(o["component"], o.get("concern")): o for o in overrides}

    findings: dict[tuple, dict] = {}
    for z in zones:
        key = (z["component"], z["concern"])
        f = findings.get(key)
        if f is None:
            f = findings[key] = {
                "component": z["component"],
                "concern": z["concern"],
                "zone_source": z["source"],  # who flagged the zone (vision)
                "measurement": None,
                "decision_source": "human",  # default: unmeasured -> human judges
                "human_override": False,
                "result": "concern",         # unmeasured zones stay a concern until a human clears them
                "note": None,
                "evidence": [],
            }
        if z["image"] not in f["evidence"]:
            f["evidence"].append(z["image"])

    for (component, concern), f in findings.items():
        m = by_component.get(component)
        if m is not None and concern in MEASURABLE_CONCERNS:
            f["measurement"] = {
                "value_mm": m["value_mm"],
                "limit_mm": m["limit_mm"],
                "source": m["source"],
                "result": m["result"],
            }
            f["decision_source"] = "metrology"
            f["result"] = m["result"]

        o = override_key.get((component, concern)) or override_key.get((component, None))
        if o is not None:
            # human wins always; the measured value stays on record untouched
            f["decision_source"] = "human"
            f["human_override"] = True
            f["result"] = o["result"]
            f["note"] = o.get("note")

    return list(findings.values())
