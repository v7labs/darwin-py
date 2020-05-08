from . import coco, pascalvoc

supported_formats = [
    ("pascalvoc", pascalvoc.export),
    ("coco", coco.export),
]
