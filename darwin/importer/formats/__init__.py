from functools import partial
from typing import List

from jsonschema import validate

from darwin.datatypes import ImporterFormat

from . import (
    coco,
    csvtags,
    csvtagsvideo,
    darwin,
    dataloop,
    labelbox,
    pascalvoc,
    superannotate,
)

supported_formats: List[ImporterFormat] = [
    ("superannotate", superannotate.parse_path),
    ("labelbox", labelbox.parse_path),
    ("pascal_voc", pascalvoc.parse_path),
    ("dataloop", dataloop.parse_path),
    ("csv_tags", csvtags.parse_path),
    ("csv_tags_video", csvtagsvideo.parse_path),
    ("coco", coco.parse_path),
    ("darwin", darwin.parse_path),
]
