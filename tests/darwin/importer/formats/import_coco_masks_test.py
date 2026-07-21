from darwin.importer.formats import coco

CAT_RLE = {"counts": [3, 2, 1, 1, 5], "size": [3, 4]}
DOG_RLE = {"counts": [1, 2, 2, 1, 6], "size": [3, 4]}
CANONICAL_DENSE_RLE = [0, 1, 1, 2, 0, 1, 2, 1, 1, 1, 0, 2, 2, 2, 0, 2]

CATEGORIES = {10: {"id": 10, "name": "cat"}, 20: {"id": 20, "name": "dog"}}


def _rle_annotation(annotation_id, category_id, segmentation, iscrowd=0):
    return {
        "id": annotation_id,
        "image_id": 1,
        "category_id": category_id,
        "iscrowd": iscrowd,
        "segmentation": segmentation,
        "bbox": [],
        "area": 0,
    }


class TestBuildMaskAnnotations:
    def test_two_instances_synthesize_masks_and_raster_layer(self):
        annotations = coco._build_mask_annotations(
            [
                _rle_annotation(100, 10, CAT_RLE),
                _rle_annotation(200, 20, DOG_RLE),
            ],
            CATEGORIES,
        )

        assert len(annotations) == 3
        cat_mask, dog_mask, raster_layer = annotations

        assert cat_mask.annotation_class.name == "cat"
        assert cat_mask.annotation_class.annotation_type == "mask"
        assert dog_mask.annotation_class.name == "dog"
        assert dog_mask.annotation_class.annotation_type == "mask"
        assert cat_mask.id and dog_mask.id and cat_mask.id != dog_mask.id

        assert raster_layer.annotation_class.name == "__raster_layer__"
        assert raster_layer.annotation_class.annotation_type == "raster_layer"
        assert raster_layer.data["total_pixels"] == 12
        assert raster_layer.data["dense_rle"] == CANONICAL_DENSE_RLE
        assert raster_layer.data["mask_annotation_ids_mapping"] == {
            cat_mask.id: 1,
            dog_mask.id: 2,
        }

    def test_overlap_later_annotation_wins(self):
        # A = 2x2 top-left block, B = 2x2 block at rows 1-2 / cols 1-2.
        # They overlap at pixel (1,1); B is later so it wins there.
        # Expected label map (row-major):
        #   1 1 0 0
        #   1 2 2 0
        #   0 2 2 0
        a_rle = {"counts": [0, 2, 1, 2, 7], "size": [3, 4]}
        b_rle = {"counts": [4, 2, 1, 2, 3], "size": [3, 4]}

        annotations = coco._build_mask_annotations(
            [_rle_annotation(1, 10, a_rle), _rle_annotation(2, 20, b_rle)],
            CATEGORIES,
        )

        raster_layer = annotations[-1]
        assert raster_layer.data["dense_rle"] == [
            1,
            2,
            0,
            2,
            1,
            1,
            2,
            2,
            0,
            2,
            2,
            2,
            0,
            1,
        ]

    def test_fully_occluded_mask_is_dropped(self):
        # A = single pixel (0,0); B = 2x2 top-left block covering it entirely.
        a_rle = {"counts": [0, 1, 11], "size": [3, 4]}
        b_rle = {"counts": [0, 2, 1, 2, 7], "size": [3, 4]}

        annotations = coco._build_mask_annotations(
            [_rle_annotation(1, 10, a_rle), _rle_annotation(2, 20, b_rle)],
            CATEGORIES,
        )

        assert len(annotations) == 2  # dog mask + raster layer only
        dog_mask, raster_layer = annotations
        assert dog_mask.annotation_class.name == "dog"
        assert raster_layer.data["mask_annotation_ids_mapping"] == {dog_mask.id: 2}
        assert 1 not in raster_layer.data["dense_rle"][0::2]

    def test_size_mismatch_and_bad_counts_are_skipped_not_raised(self):
        wrong_size = {"counts": [0, 4], "size": [2, 2]}
        wrong_total = {"counts": [3, 2], "size": [3, 4]}

        annotations = coco._build_mask_annotations(
            [
                _rle_annotation(1, 10, CAT_RLE),
                _rle_annotation(2, 20, wrong_size),
                _rle_annotation(3, 20, wrong_total),
            ],
            CATEGORIES,
        )

        assert len(annotations) == 2  # cat mask + raster layer
        assert annotations[0].annotation_class.name == "cat"

    def test_no_annotations_returns_empty(self):
        assert coco._build_mask_annotations([], CATEGORIES) == []
