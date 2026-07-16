# Training the damage-zoning model (Colab GPU)

The demo laptop has no CUDA GPU, so fine-tuning runs on free Colab; **inference
is always local** (weights on disk, see `backend/vision/yolo_service.py`).

Dataset: `Container Damage/` at the repo root (Roboflow `conStatus` export,
YOLO format, classes `Dent / Hole / Rust`, ~4k train images).
Base weights: `YOLO_models/yolov5x.pt` (stock COCO). If the upload is too slow,
the script falls back to auto-downloading `yolov5xu.pt` — same architecture,
ultralytics format.

## Steps

1. Zip the dataset folder on the laptop (PowerShell):

   ```powershell
   Compress-Archive -Path "C:\Laptop files\TSAJ-Hackathon\Container Damage" -DestinationPath container-damage.zip
   ```

2. New Colab notebook → Runtime → Change runtime type → **GPU (T4)**.

3. Cell 1 — deps:

   ```
   !pip -q install ultralytics
   ```

4. Cell 2 — upload `container-damage.zip`, this file (`train_colab.py`), and
   optionally `yolov5x.pt` (files panel on the left, or `google.colab.files.upload()`), then:

   ```
   !unzip -q container-damage.zip
   ```

5. Cell 3 — train (~1–2 h on T4; batch auto-sized to GPU memory):

   ```
   !python train_colab.py --dataset "Container Damage" --base yolov5x.pt --epochs 50
   ```

6. Cell 4 — download the result:

   ```
   from google.colab import files
   files.download("damage.pt")
   ```

7. On the laptop, save it as:

   ```
   container-inspect/assets/weights/damage.pt
   ```

   Restart the backend container. `POST /v0/inspections/{id}/run-vision?fresh=true`
   now runs real local inference and refreshes `assets/vision_cache.json`
   (plain `run-vision` keeps serving the deterministic cache — use that on stage).

## Sanity check

`val mAP50` is printed at the end. Anything ≥ ~0.5 is fine for zoning/triage —
vision only points at regions; measurement + human sign-off make the decision.
