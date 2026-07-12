"""M3: mock metrology - reads pre-recorded mm values from assets/measurements.json."""


def measure(component: str) -> float:
    """Return the pre-recorded mm value for a component zone."""
    raise NotImplementedError("M3: mock metrology reading pre-recorded values")
