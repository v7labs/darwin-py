from . import coco, pascalvoc, semantic_mask, instance_mask

supported_formats = [
    ("pascal_voc", pascalvoc.export),
    ("coco", coco.export),
    ("semantic_mask", semantic_mask.export),
    ("instance_mask", instance_mask.export),
]
