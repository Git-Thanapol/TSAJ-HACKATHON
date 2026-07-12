# Demo assets (drop-in, pre-recorded — nothing here is fetched at runtime)

Required before M2–M4; see Core Ideas\HANDOV~2.MD §2 "Assets".

- `photos/` — 5–10 real container photos with visible dent/rust/hole (M2 YOLO input)
- `weights/yolov12*.pt` — local YOLOv12 weights; inference is ALWAYS local (M2)
- `measurements.json` — pre-recorded mm values the mock metrology returns (M3)
- `boxes/<container_id>.glb` — container 3D twin model (M4)
- `boxes/<container_id>.laz|.ply` — point cloud kept as measurement ground truth (M4)
