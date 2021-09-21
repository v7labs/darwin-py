from pathlib import Path
from pprint import pprint

from darwin.torch.dataset import BoundingBoxDetectionDataset
from PIL import Image
from tests.utils import DarwinDatasetFS, TestDarwinDataset


def test_bbox_dataset(tmp_path: Path):
    # let's create the test dataset
    tds = TestDarwinDataset(fs=DarwinDatasetFS(Path(tmp_path) / ".darwin/datasets/tmp"))
    tds.build()
    ds = BoundingBoxDetectionDataset(dataset_path=tds.fs.root, release_name="latest")

    assert len(ds) == len(tds)

    for i, (img, target) in enumerate(ds):
        # get the original index form the path
        original_path = ds.annotations_path[i]
        real_idx = int(original_path.stem)
        ann = tds[real_idx][1]
        assert img.size[0] == 100
        assert img.size[1] == 100

        correct_shape = len(ann.annotations)
        for (k, v) in target.items():
            # image_id is just one number
            if not "image_id" == k:
                assert v.shape[0] == correct_shape

        assert target["image_id"].shape[0] == 1
        bboxes = target["boxes"]
        assert bboxes.shape[-1] == 4
        for i, ann_el in enumerate(ann.annotations):
            bbox = bboxes[i]
            bbox_ann = ann_el.bounding_box

            assert bbox[0].item() == bbox_ann.h
            assert bbox[1].item() == bbox_ann.w
            assert bbox[2].item() == bbox_ann.x
            assert bbox[3].item() == bbox_ann.y
