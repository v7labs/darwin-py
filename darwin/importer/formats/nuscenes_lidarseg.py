from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.lidar.nuscenes import parse_nuscenes_lidarseg


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    nuScenes-lidarseg / panoptic point masks: triggers on ``panoptic.json`` (instances + classes)
    or, when there is none next to it, on ``lidarseg.json`` (classes only). One annotation file
    per scene (items named ``<scene name>.lidar.zip``).
    """
    path = Path(path)
    if path.name == "panoptic.json":
        return parse_nuscenes_lidarseg(path.parent, panoptic=True)
    if path.name == "lidarseg.json" and not (path.parent / "panoptic.json").exists():
        return parse_nuscenes_lidarseg(path.parent)
    return None
