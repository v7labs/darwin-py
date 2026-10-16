from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    A PandaSet sequence, triggered once by the first file of ``annotations/cuboids`` (or of
    ``annotations/semseg`` when the sequence has no cuboids). Trusted data only (pickles).
    """
    kind = path.parent.name
    if not path.name.endswith(".pkl.gz") or kind not in ("cuboids", "semseg"):
        return None
    annotations = path.parent.parent
    if annotations.name != "annotations":
        return None
    if kind == "semseg" and (annotations / "cuboids").is_dir():
        return None
    first = min(path.parent.glob("*.pkl.gz"), key=lambda p: (len(p.name), p.name))
    if path.name != first.name:
        return None
    from darwin.lidar.pandaset import parse_pandaset

    return parse_pandaset(annotations.parent)
