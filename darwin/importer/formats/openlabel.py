from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.lidar.openlabel import is_openlabel, parse_openlabel


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses an ASAM OpenLABEL 1.0 ``.json`` file (root key ``openlabel``) into the 3D annotations
    of one ``pointcloud`` item, or returns ``None`` for any other file.
    """
    if not is_openlabel(path):
        return None
    return parse_openlabel(path)
