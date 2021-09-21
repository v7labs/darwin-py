import dataclasses
import json
import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

import darwin.dataset.data as D


@dataclass
class DarwinDatasetFS:
    """
    Handy mapping to the correct darwin's dataset folder structure in the file system.

    .. warning::
        `DarwinDatasetFS` works only on mac and linux
    """

    root: Path = Path("/tmp/.darwin/datasets/tmp")
    images: Path = root / "images"
    releases: Path = root / "releases"
    release: Path = releases / "latest"
    annotations: Path = release / "annotations"
    lists: Path = release / "lists"

    def __post_init__(self):
        self.mkdirs()

    def mkdirs(self):
        for f in self.__dict__.values():
            f.mkdir(exist_ok=True, parents=True)

    def clear(self):
        shutil.rmtree(self.root)


@dataclass
class TestDarwinDataset:
    """
    This dataset creates random annotations directly on the file system. It uses `DarwinDatasetFS` to know where to create the files

    Usage:
        >>> tds = TestDarwinDataset()
        >>> img, ann = tds[0]
        >>> tds.build() # all the images/annotations are now in `/tmp/.darwin/datasets/tmp`

    .. warning::
        Only annotations with `bounding_box` are currently created.


    """

    fs: DarwinDatasetFS = DarwinDatasetFS()
    size: Tuple[int, int] = (100, 100)
    classes: List[str] = field(default_factory=lambda: ["a", "b", "c"])
    idx: int = 0
    n: int = 10

    def make_random_image(self, idx: int) -> Image.Image:
        canvas = np.zeros((*self.size, 3), dtype=np.uint8)
        img = Image.fromarray(canvas)
        return img

    def make_annotation(self, idx: int) -> D.AnnotationFile:
        random.seed(idx)
        return D.AnnotationFile(
            dataset="foo",
            image=D.Image(*self.size, f"{idx}.png", f"{idx}.png"),
            annotations=[
                D.BoundingBoxAnnotation(
                    name=self.classes[c_idx % len(self.classes)],
                    bounding_box=D.BoundingBox(
                        random.randint(0, self.size[0] // 5),
                        random.randint(0, self.size[0] // 5),
                        random.randint(0, self.size[0]),
                        random.randint(0, self.size[0]),
                    ),
                )
                for c_idx in range(len(self.classes))
            ],
        )

    def __getitem__(self, idx) -> Tuple[Image.Image, D.AnnotationFile]:
        return self.make_random_image(idx), self.make_annotation(idx)

    def build(self):
        self.fs.clear()
        self.fs.mkdirs()
        for idx in range(len(self)):
            img, ann = self[idx]
            # serialize them
            img.save(self.fs.images / f"{idx}.png")
            with (self.fs.annotations / f"{idx}.json").open("w") as f:
                json.dump(dataclasses.asdict(ann), f, indent=4)
        # write list
        lists_file_names = ["classes_bounding_box.txt", "classes_polygon.txt", "classes_tag.txt"]
        for list_file_name in lists_file_names:
            with (self.fs.lists / list_file_name).open("w") as f:
                f.write("\n".join(self.classes))

    def __len__(self):
        return self.n
