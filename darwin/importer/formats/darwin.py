from pathlib import Path
from typing import Optional

import darwin.datatypes as dt
from darwin.utils import parse_darwin_json


def parse_path(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".json":
        return None
    return parse_darwin_json(path, 0)
