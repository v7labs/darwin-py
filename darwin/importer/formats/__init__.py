from functools import partial
from typing import List

from jsonschema import validate

from darwin.datatypes import ImporterFormat
from darwin.importer.formats.labelbox_schemas import labelbox_export

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

labelbox_validator = partial(validate, schema=labelbox_export)

supported_formats: List[ImporterFormat] = [
    ("superannotate", superannotate.parse_path),
    ("labelbox", partial(labelbox.parse_path, validate=labelbox_validator)),
    ("pascal_voc", pascalvoc.parse_path),
    ("dataloop", dataloop.parse_path),
    ("csv_tags", csvtags.parse_path),
    ("csv_tags_video", csvtagsvideo.parse_path),
    ("coco", coco.parse_path),
    ("darwin", darwin.parse_path),
]
