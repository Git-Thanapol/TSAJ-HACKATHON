"""M3: mock metrology - reads pre-recorded mm values from assets/measurements.json.

Real metrology (LiDAR/photogrammetry) is out of scope by design: this module is
the swappable stand-in that returns the measured number. The demo laptop never
attempts live mm-accurate measurement.
"""
import json
import os

MEASUREMENTS_FILE = "measurements.json"


def load_measurements(assets_dir: str) -> dict:
    """{container_id: {component: value_mm}} — pre-recorded by the team."""
    try:
        with open(os.path.join(assets_dir, MEASUREMENTS_FILE), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    data.pop("_comment", None)
    return data


def measure(container_id: str, component: str, assets_dir: str) -> float | None:
    """Return the pre-recorded mm value for a component zone (None = not measured)."""
    return load_measurements(assets_dir).get(container_id, {}).get(component)
