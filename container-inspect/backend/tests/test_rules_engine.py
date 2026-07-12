import os

import pytest

from rules.engine import evaluate, load_rulesets

STANDARDS_DIR = os.path.join(os.path.dirname(__file__), "..", "standards")


def test_load_both_profiles():
    rulesets = load_rulesets(STANDARDS_DIR)
    assert set(rulesets) == {"IICL-6", "Domestic-Lite"}
    iicl = rulesets["IICL-6"]
    assert iicl.mode == "measured"
    assert iicl.components["side_panel"].limit_mm == 35
    assert iicl.components["corner_post"].limit_mm == 20
    assert iicl.components["corner_post"].any_number_of_dents is True
    assert iicl.components["floor_height"].limit_mm == 5
    assert iicl.components["oil_stain"].method == "human"
    lite = rulesets["Domestic-Lite"]
    assert lite.mode == "appearance_only"
    assert lite.components["appearance"].zones_from == "vision"


def test_evaluate_pass_and_concern():
    rulesets = load_rulesets(STANDARDS_DIR)
    side_panel = rulesets["IICL-6"].components["side_panel"]
    assert evaluate(side_panel, 34.9) == "pass"
    assert evaluate(side_panel, 35.0) == "pass"     # at limit = pass
    assert evaluate(side_panel, 41.0) == "concern"  # the demo's 41 > 35 case


def test_evaluate_rejects_unlimited_component():
    rulesets = load_rulesets(STANDARDS_DIR)
    oil = rulesets["IICL-6"].components["oil_stain"]
    with pytest.raises(ValueError):
        evaluate(oil, 1.0)
