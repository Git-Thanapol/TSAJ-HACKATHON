from models import ComponentRule, Finding, InspectionRecord, Measurement, Ruleset


def test_ruleset_from_dict_measured():
    rs = Ruleset.model_validate({
        "standard": "IICL-6",
        "version": "2016-08-01",
        "mode": "measured",
        "components": {
            "side_panel": {"measure": "internal_cube_intrusion", "limit_mm": 35, "method": "metrology"},
            "oil_stain": {"measure": "transferable", "accept_if": False, "method": "human"},
        },
    })
    assert rs.components["side_panel"].limit_mm == 35
    assert rs.components["oil_stain"].limit_mm is None
    assert rs.components["oil_stain"].accept_if is False


def test_ruleset_appearance_only():
    rs = Ruleset.model_validate({
        "standard": "Domestic-Lite",
        "version": "2026-01",
        "mode": "appearance_only",
        "components": {
            "appearance": {"measure": "human_review", "method": "human", "zones_from": "vision"},
        },
    })
    assert rs.mode == "appearance_only"
    assert rs.components["appearance"].zones_from == "vision"


def test_inspection_record_roundtrip():
    rec = InspectionRecord(
        inspection_id="insp_01",
        container_id="MSKU1234565",
        direction="inbound",
        standard={"name": "IICL-6", "version": "2016-08-01"},
        status="signed",
        findings=[Finding(
            component="side_panel_left",
            concern="dent",
            zone_source="vision",
            measurement=Measurement(value_mm=41, limit_mm=35, source="metrology", result="concern"),
            decision_source="human",
            human_override=False,
            evidence=["img/crop_12.jpg"],
        )],
    )
    dumped = rec.model_dump()
    assert dumped["findings"][0]["measurement"]["result"] == "concern"
    assert dumped["signed_by"] is None
