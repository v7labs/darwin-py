from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """Argoverse 2 ``annotations.feather`` (log directory next to it) -> 3D cuboid tracks."""
    if path.name != "annotations.feather":
        return None
    from darwin.lidar.av2 import parse_av2

    return parse_av2(path)
