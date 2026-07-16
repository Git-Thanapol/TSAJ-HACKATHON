from pathlib import Path
from typing import Literal

import yaml

from models import ComponentRule, Ruleset


def load_rulesets(standards_dir: str) -> dict[str, Ruleset]:
    """Load every *.yaml in standards_dir as a versioned Ruleset, keyed by standard name."""
    rulesets: dict[str, Ruleset] = {}
    for path in sorted(Path(standards_dir).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        ruleset = Ruleset.model_validate(data)
        rulesets[ruleset.standard] = ruleset
    return rulesets


def match_rule(ruleset: Ruleset, component: str) -> tuple[str, ComponentRule] | None:
    """Find the rule for a zone component: exact name, then prefix.

    Photo zones are specific ('side_panel_left'); rulesets are generic
    ('side_panel'). Components with no matching rule fall to human review.
    """
    rule = ruleset.components.get(component)
    if rule is not None:
        return component, rule
    for name, rule in ruleset.components.items():
        if component.startswith(name):
            return name, rule
    return None


def evaluate(rule: ComponentRule, value_mm: float) -> Literal["pass", "concern"]:
    """Value-vs-limit check. 'concern', never 'fail' - the human signs the decision."""
    if rule.limit_mm is None:
        raise ValueError(f"component rule '{rule.measure}' has no mm limit; method={rule.method}")
    return "pass" if value_mm <= rule.limit_mm else "concern"
