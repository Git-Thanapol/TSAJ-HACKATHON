import re
from typing import Literal

from pydantic import BaseModel

# ISO 6346 letter values: A=10, then +1 each, skipping multiples of 11 (11, 22, 33).
_LETTER_VALUES = dict(zip(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24,
     25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38],
))

_ID_RE = re.compile(r"[A-Z]{4}[0-9]{7}")


def validate_iso6346(container_id: str) -> bool:
    """ISO 6346 container ID check-digit validation (4 letters + 6 digits + check digit)."""
    if not container_id or not _ID_RE.fullmatch(container_id):
        return False
    total = sum(
        (_LETTER_VALUES[ch] if ch.isalpha() else int(ch)) * (2 ** i)
        for i, ch in enumerate(container_id[:10])
    )
    return (total % 11) % 10 == int(container_id[10])


class ComponentRule(BaseModel):
    measure: str
    limit_mm: float | None = None
    method: Literal["metrology", "human"]
    any_number_of_dents: bool = False
    accept_if: bool | None = None
    zones_from: str | None = None


class Ruleset(BaseModel):
    standard: str
    version: str
    mode: Literal["measured", "appearance_only"]
    components: dict[str, ComponentRule]


class Measurement(BaseModel):
    value_mm: float
    limit_mm: float
    source: str
    result: Literal["pass", "concern"]


class Finding(BaseModel):
    component: str
    concern: str
    zone_source: str                      # which source flagged the zone (e.g. "vision")
    measurement: Measurement | None = None
    decision_source: str                  # precedence: Human > Metrology > Vision
    human_override: bool = False
    # additive to the handover schema: final post-precedence disposition + human note
    result: Literal["pass", "concern"] | None = None
    note: str | None = None
    evidence: list[str] = []


class StandardRef(BaseModel):
    name: str
    version: str


class InspectionRecord(BaseModel):
    inspection_id: str
    container_id: str
    iso_type: str | None = None
    direction: Literal["inbound", "outbound"]
    standard: StandardRef
    status: str
    findings: list[Finding] = []
    twin: dict[str, str] | None = None
    signed_by: str | None = None
    signed_at: str | None = None
    prev_hash: str | None = None
    hash: str | None = None
