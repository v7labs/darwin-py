from functools import partial
from typing import List

from darwin.datatypes import ImporterFormat
from darwin.importer.formats.labelbox_schemas import labelbox_export

from . import coco, csvtags, csvtagsvideo, darwin, dataloop, labelbox, pascalvoc

supported_formats: List[ImporterFormat] = [
    ("labelbox", partial(labelbox.parse_file, schema=labelbox_export)),
    ("pascal_voc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
    ("csv_tags", csvtags.parse_file),
    ("csv_tags_video", csvtagsvideo.parse_file),
    ("coco", coco.parse_file),
    ("darwin", darwin.parse_file),
]
