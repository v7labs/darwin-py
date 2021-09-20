import os
from pathlib import Path

import torch
from torch import nn
from io import StringIO

os.environ["DARWIN_BASE_URL"] = "http://localhost:4242/"

API_KEY = "9ouYpmX.a4RuCedxjc4G7Z6hLkkkJwri6CM7EbQf"
from darwin.torch.dataset import ClassificationDataset


ann = """
{
    "dataset": "test3",
    "image": {
        "width": 200,
        "height": 200,
        "original_filename": "0.png",
        "filename": "0.png",
        "url": null,
        "thumbnail_url": null,
        "path": "/",
        "workview_url": null
    },
    "annotations": [
        {
            "name": "green",
            "tag": {}
        },
        {
            "name": "blue",
            "tag": {}
        }
    ]
}
"""


class FakeAnnotationFile:
    def __init__(self, ann: str):
        self.buff = StringIO(ann)

    def open(self, *args, **kwargs) -> StringIO:
        return self.buff


FakeAnnotationFile(ann).open()

ds = ClassificationDataset(
    dataset_path=Path("/home/zuppif/.darwin/datasets/v7/test3"), release_name="foo"
)

print(ds[0][1].shape[0])

# ds = ClassificationDataset(Path("~/"))

# tags = [0, 1]

# one_hot = torch.zeros(len(tags))
# out = torch.randn_like(one_hot)
# one_hot[0] = 1
# print(one_hot)

# criterion = nn.BCEWithLogitsLoss()

# print(criterion(out, one_hot))
