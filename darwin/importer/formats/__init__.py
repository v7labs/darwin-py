from . import coco, csvtags, csvtagsvideo, darwin, dataloop, pascalvoc

supported_formats = [
    ("pascal_voc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
    ("csv_tags", csvtags.parse_file),
    ("csv_tags_video", csvtagsvideo.parse_file),
    ("coco", coco.parse_file),
    ("darwin", darwin.parse_file),
]
