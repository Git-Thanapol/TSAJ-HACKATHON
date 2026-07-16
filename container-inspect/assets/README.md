# Demo assets (drop-in, pre-recorded — nothing here is fetched at runtime)

Required before M2–M4; see Core Ideas\HANDOV~2.MD §2 "Assets".

- `photos/<container_id>/` — real container photos with visible dent/rust/hole (M2 YOLO input)
- `photos.json` — manifest: container_id → [{file, component}] (component = zoning heuristic)
- `vision_cache.json` — cached detections; pre-seeded from dataset labels so the
  demo runs before trained weights land, refreshed by `run-vision?fresh=true`
- `weights/damage.pt` — fine-tuned YOLO weights (see ../training/README.md);
  inference is ALWAYS local (M2)
- `measurements.json` — pre-recorded mm values the mock metrology returns (M3)
- `boxes/<container_id>.glb` — container 3D twin model (M4)
- `boxes/<container_id>.laz|.ply` — point cloud kept as measurement ground truth (M4)
