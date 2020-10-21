from functools import partial

from . import coco, cvat, dataloop, instance_mask, pascalvoc, semantic_mask, darwin_image

supported_formats = [
    ("coco", coco.export),
    ("cvat", cvat.export),
    ("dataloop", dataloop.export),
    ("instance-mask", instance_mask.export),
    ("pascal_voc", pascalvoc.export),
    ("semantic-mask", partial(semantic_mask.export, mode="rgb")),
    ("semantic-mask-grey", partial(semantic_mask.export, mode="grey")),
    ("semantic-mask-index", partial(semantic_mask.export, mode="index")),
    ("darwin-image", darwin_image.export),
    ("video-split", darwin_image.export),
]
