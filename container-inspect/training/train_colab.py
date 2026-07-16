"""Fine-tune YOLO on the conStatus container-damage dataset (Dent/Hole/Rust).

Runs on Colab GPU (see training/README.md for the cell-by-cell recipe).
Training happens off-laptop; the resulting best.pt is copied back to
container-inspect/assets/weights/damage.pt and ALL inference stays local.
"""
import argparse
import shutil
from pathlib import Path

import yaml
from ultralytics import YOLO


def patch_data_yaml(dataset_dir: Path) -> Path:
    """Rewrite Roboflow's relative split paths ('../train/images') to absolute.

    Roboflow yamls resolve those relative to the yaml's parent directory,
    which points one level too high once the zip is extracted elsewhere.
    """
    data_yaml = dataset_dir / "data.yaml"
    data = yaml.safe_load(data_yaml.read_text())
    for split, sub in (("train", "train/images"), ("val", "valid/images"), ("test", "test/images")):
        if (dataset_dir / sub).is_dir():
            data[split] = str((dataset_dir / sub).resolve())
    patched = dataset_dir / "data.abs.yaml"
    patched.write_text(yaml.safe_dump(data))
    return patched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="Container Damage", help="extracted dataset root (holds data.yaml)")
    ap.add_argument("--base", default="yolov5x.pt", help="base weights; falls back to yolov5xu.pt download")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=-1, help="-1 = AutoBatch (fit GPU memory)")
    ap.add_argument("--out", default="damage.pt", help="where to copy the best checkpoint")
    args = ap.parse_args()

    data_yaml = patch_data_yaml(Path(args.dataset))

    base = args.base
    if not Path(base).exists():
        # ultralytics-format YOLOv5 checkpoint, auto-downloaded by the library
        base = "yolov5xu.pt"
        print(f"--base {args.base} not found; using {base} (auto-download)")

    model = YOLO(base)
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project="runs",
        name="damage",
    )
    metrics = model.val(data=str(data_yaml))
    print("val mAP50:", metrics.box.map50)

    best = Path(model.trainer.best)
    shutil.copyfile(best, args.out)
    print(f"copied {best} -> {args.out}")
    print("Put this file at container-inspect/assets/weights/damage.pt on the demo laptop.")


if __name__ == "__main__":
    main()
