from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.lidar.semantic_kitti import label_files, parse_semantic_kitti


@lru_cache(maxsize=None)
def _first_label(directory: Path) -> Optional[Path]:
    files = label_files(directory)
    return files[0] if files else None


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    SemanticKITTI ``labels/*.label`` -> ``point_mask_3d`` annotations. The importer calls this for
    every file, so only the first ``.label`` file of a directory triggers parsing that directory.
    """
    path = Path(path)
    if path.suffix != ".label" or _first_label(path.parent) != path:
        return None
    return parse_semantic_kitti(path.parent)
