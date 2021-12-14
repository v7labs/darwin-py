from functools import partial
from typing import List

from jsonschema import validate

from darwin.datatypes import ImporterFormat
from darwin.importer.formats.labelbox_schemas import labelbox_export

from . import coco, csvtags, csvtagsvideo, darwin, dataloop, labelbox, pascalvoc

validate_with_schema = partial(validate, schema=labelbox_export)

supported_formats: List[ImporterFormat] = [
    ("labelbox", partial(labelbox.parse_file, validate=validate_with_schema)),
    ("pascal_voc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
    ("csv_tags", csvtags.parse_file),
    ("csv_tags_video", csvtagsvideo.parse_file),
    ("coco", coco.parse_file),
    ("darwin", darwin.parse_file),
]
