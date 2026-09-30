from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.importer.formats import coco
from darwin.utils import attempt_decode


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given ``coco`` file like the ``coco`` importer, but imports RLE
    segmentations as Darwin raster ``mask`` annotations (plus one
    ``raster_layer`` per image) instead of converting them to polygons.
    Polygon segmentations are imported as polygons, unchanged.

    Parameters
    ----------
    path : Path
        The ``Path`` to the ``coco`` file.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        Returns ``None`` if the given file is not in ``json`` format, or
        ``List[dt.AnnotationFile]`` otherwise.
    """
    if path.suffix != ".json":
        return None
    data = attempt_decode(path)
    return list(coco.parse_json(path, data, rle_as_masks=True))
