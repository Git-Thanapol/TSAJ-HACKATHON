"""M2: local YOLO zoning service. Vision NEVER emits pass/fail - zones only.

Weights are loaded from disk (WEIGHTS_PATH) and inference is always local —
never a hosted/cloud API. Detections are cached in <assets>/vision_cache.json
so the stage demo is deterministic and works before trained weights exist
(the cache ships pre-seeded from the dataset's ground-truth labels).
"""
import json
import os
import threading

CACHE_FILE = "vision_cache.json"

_model = None
_model_lock = threading.Lock()


class VisionUnavailable(RuntimeError):
    """No usable weights and no cached detections for the requested photos."""


def weights_path() -> str:
    return os.environ.get("WEIGHTS_PATH", "/assets/weights/damage.pt")


def _load_model():
    global _model
    with _model_lock:
        if _model is None:
            path = weights_path()
            if not os.path.exists(path):
                raise VisionUnavailable(f"weights not found at {path}")
            # heavy import kept local so the API (and tests) run without torch installed
            from ultralytics import YOLO
            _model = YOLO(path)
    return _model


def _cache_path(assets_dir: str) -> str:
    return os.path.join(assets_dir, CACHE_FILE)


def _read_cache(assets_dir: str) -> dict:
    try:
        with open(_cache_path(assets_dir), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _write_cache(assets_dir: str, cache: dict) -> None:
    try:
        with open(_cache_path(assets_dir), "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError:
        pass  # read-only assets mount: serve fresh results without persisting


def run_zoning(photos: list[dict], assets_dir: str, fresh: bool = False) -> list[dict]:
    """Return zones of concern for manifest entries [{file, component}, ...].

    Zone shape: {image, component, concern, bbox [cx,cy,w,h normalized],
    confidence, source: "vision"}. Concern is a damage class (dent/hole/rust),
    never a pass/fail — the rules engine + human decide, vision only points.

    Cached detections are preferred (fast + deterministic on stage) unless
    fresh=True forces local re-inference and refreshes the cache.
    """
    cache = _read_cache(assets_dir)
    if not fresh and all(p["file"] in cache for p in photos):
        return [zone for p in photos for zone in cache[p["file"]]]

    model = _load_model()
    all_zones = []
    for p in photos:
        result = model.predict(os.path.join(assets_dir, p["file"]), verbose=False)[0]
        zones = [
            {
                "image": p["file"],
                "component": p["component"],
                "concern": result.names[int(box.cls)].lower(),
                "bbox": [round(float(v), 4) for v in box.xywhn[0]],
                "confidence": round(float(box.conf), 3),
                "source": "vision",
            }
            for box in result.boxes
        ]
        cache[p["file"]] = zones
        all_zones.extend(zones)
    _write_cache(assets_dir, cache)
    return all_zones
