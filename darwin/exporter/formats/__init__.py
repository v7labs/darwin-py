from functools import partial
from typing import List

from darwin.datatypes import ExporterFormat

from . import coco, cvat, dataloop, instance_mask, pascalvoc, semantic_mask

supported_formats: List[ExporterFormat] = [
    ("coco", coco.export),
    ("cvat", cvat.export),
    ("dataloop", dataloop.export),
    ("instance-mask", instance_mask.export),
    ("pascal_voc", pascalvoc.export),
    ("semantic-mask", partial(semantic_mask.export, mode="rgb")),
    ("semantic-mask-grey", partial(semantic_mask.export, mode="grey")),
    ("semantic-mask-index", partial(semantic_mask.export, mode="index")),
]
