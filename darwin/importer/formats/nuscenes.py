from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.lidar.nuscenes import parse_nuscenes


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    nuScenes boxes: triggers on ``<dataroot>/<version>/sample_annotation.json`` and returns one
    ``pointcloud`` annotation file per scene (items named ``<scene name>.lidar.zip``).
    """
    path = Path(path)
    if path.name != "sample_annotation.json":
        return None
    return parse_nuscenes(path.parent)
