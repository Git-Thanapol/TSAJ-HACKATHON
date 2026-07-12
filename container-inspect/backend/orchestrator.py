"""Pipeline: vision -> metrology -> rules -> fusion -> record.

M1 skeleton only. Each stage is filled in by its milestone (M2 vision, M3 rest).
"""
from metrology import mock as metrology
from vision import yolo_service
import fusion


def run_pipeline(inspection_id: str) -> None:
    raise NotImplementedError("wired stage by stage in M2/M3")
