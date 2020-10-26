from pathlib import Path
from typing import Optional

import darwin.datatypes as dt
from darwin.utils import parse_darwin_json


def parse_file(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".json":
        return
    return parse_darwin_json(path, 0)
