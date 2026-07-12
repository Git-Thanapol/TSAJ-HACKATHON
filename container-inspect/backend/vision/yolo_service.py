"""M2: local YOLOv12 zoning service. Vision NEVER emits pass/fail - zones only."""


def run_zoning(image_paths: list[str]) -> list[dict]:
    """Return zones of concern: [{component, concern, bbox, confidence}, ...]."""
    raise NotImplementedError("M2: local YOLOv12 inference from weights on disk")
