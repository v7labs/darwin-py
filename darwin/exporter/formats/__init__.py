from . import coco, cvat, dataloop, instance_mask, pascalvoc, semantic_mask

supported_formats = [
    ("coco", coco.export),
    ("cvat", cvat.export),
    ("dataloop", dataloop.export),
    ("pascal_voc", pascalvoc.export),
    ("semantic-mask", semantic_mask.export),
    ("instance-mask", instance_mask.export),
]
