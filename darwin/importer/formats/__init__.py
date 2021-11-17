from typing import List

from darwin.datatypes import ImporterFormat

from . import coco, csvtags, csvtagsvideo, darwin, dataloop, label_box, pascalvoc

supported_formats: List[ImporterFormat] = [
    ("labelbox", label_box.parse_file),
    ("pascal_voc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
    ("csv_tags", csvtags.parse_file),
    ("csv_tags_video", csvtagsvideo.parse_file),
    ("coco", coco.parse_file),
    ("darwin", darwin.parse_file),
]
