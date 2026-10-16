from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.lidar.kitti import (
    parse_kitti_labels,
    parse_kitti_tracking,
    parse_kitti_tracklets,
)


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    KITTI 3D labels -> LiDAR annotation files (velodyne / sensor frame):
    ``label_2/<id>.txt`` (object), ``label_02/<seq>.txt`` (tracking) and raw
    ``tracklet_labels.xml``. Calib is read from the dataset layout next to the labels.
    """
    path = Path(path)
    if path.name == "tracklet_labels.xml":
        return parse_kitti_tracklets(path)
    if path.suffix != ".txt" or not path.is_file():
        return None
    if path.parent.name == "label_2":
        return parse_kitti_labels(path)
    if path.parent.name == "label_02":
        return parse_kitti_tracking(path)
    return None
