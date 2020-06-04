from . import coco, cvat, dataloop, pascalvoc

supported_formats = [
    ("coco", coco.export),
    ("cvat", cvat.export),
    ("dataloop", dataloop.export),
    ("pascal_voc", pascalvoc.export),
]
