import json
from pathlib import Path

from darwin.exporter import exporter as darwin_exporter
from darwin.exporter.formats import coco as coco_exporter
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

    def test_missing_size_is_skipped_not_raised(self):
        missing_size = {"counts": [3, 2, 1, 1, 5]}

        annotations = coco._build_mask_annotations(
            [
                _rle_annotation(1, 10, CAT_RLE),
                _rle_annotation(2, 20, missing_size),
            ],
            CATEGORIES,
        )

        assert len(annotations) == 2  # cat mask + raster layer only
        assert annotations[0].annotation_class.name == "cat"
        assert annotations[-1].annotation_class.annotation_type == "raster_layer"

    def test_unknown_category_id_is_skipped_not_raised(self):
        annotations = coco._build_mask_annotations(
            [
                _rle_annotation(1, 10, CAT_RLE),
                _rle_annotation(2, 99, DOG_RLE),
            ],
            CATEGORIES,
        )

        assert len(annotations) == 2  # cat mask + raster layer only
        assert annotations[0].annotation_class.name == "cat"
        assert annotations[-1].annotation_class.annotation_type == "raster_layer"

    def test_image_dims_authority_ignores_malformed_leading_rle_size(self):
        # A malformed FIRST RLE claims a 2x2 canvas, but the image record is
        # actually 3x4 (image_height=3, image_width=4). The image dims must
        # win: the wrong-size RLE is skipped, and the valid CAT_RLE (which
        # matches the real 3x4 canvas) is kept instead of being skipped as
        # "mismatched" against a bogus 2x2 canvas set by the first RLE.
        #
        # CAT_RLE decodes (row-major, on a 3x4 canvas) to:
        #   0 1 1 0
        #   0 1 0 0
        #   0 0 0 0
        # i.e. flat = [0,1,1,0, 0,1,0,0, 0,0,0,0]
        # Dense RLE (value,count pairs) of that flat sequence:
        #   0x1, 1x2, 0x2, 1x1, 0x6
        # => [0, 1, 1, 2, 0, 2, 1, 1, 0, 6]
        wrong_size_first = {"counts": [0, 4], "size": [2, 2]}

        annotations = coco._build_mask_annotations(
            [
                _rle_annotation(1, 99, wrong_size_first),
                _rle_annotation(2, 10, CAT_RLE),
            ],
            CATEGORIES,
            image_height=3,
            image_width=4,
        )

        assert len(annotations) == 2  # cat mask + raster layer
        cat_mask, raster_layer = annotations
        assert cat_mask.annotation_class.name == "cat"
        assert raster_layer.data["total_pixels"] == 12
        assert raster_layer.data["dense_rle"] == [0, 1, 1, 2, 0, 2, 1, 1, 0, 6]

    def test_without_image_dims_first_rle_size_remains_authority(self):
        # Backward-compat: when image_height/image_width are not supplied
        # (positional call, as existing direct-unit callers do), the FIRST
        # RLE's own "size" continues to set the canvas, exactly as before.
        wrong_size_only = {"counts": [0, 4], "size": [2, 2]}

        annotations = coco._build_mask_annotations(
            [_rle_annotation(1, 10, wrong_size_only)],
            CATEGORIES,
        )

        assert len(annotations) == 2  # single mask + raster layer
        raster_layer = annotations[-1]
        assert raster_layer.data["total_pixels"] == 4


def _coco_json(annotations, categories=None):
    return {
        "images": [{"id": 1, "file_name": "test.png", "height": 3, "width": 4}],
        "categories": categories
        or [
            {"id": 10, "name": "cat", "supercategory": "root"},
            {"id": 20, "name": "dog", "supercategory": "root"},
        ],
        "annotations": annotations,
    }


class TestCocoMasksParsePath:
    def test_rle_annotations_import_as_masks(self, tmp_path: Path):
        from darwin.importer.formats import coco_masks

        coco_file = tmp_path / "coco.json"
        coco_file.write_text(
            json.dumps(
                _coco_json(
                    [
                        _rle_annotation(100, 10, CAT_RLE),
                        _rle_annotation(200, 20, DOG_RLE),
                    ]
                )
            )
        )

        annotation_files = coco_masks.parse_path(coco_file)

        assert annotation_files is not None and len(annotation_files) == 1
        annotation_file = annotation_files[0]
        assert annotation_file.filename == "test.png"

        types = [
            a.annotation_class.annotation_type for a in annotation_file.annotations
        ]
        assert types.count("mask") == 2
        assert types.count("raster_layer") == 1

        raster_layer = next(
            a
            for a in annotation_file.annotations
            if a.annotation_class.annotation_type == "raster_layer"
        )
        assert raster_layer.data["dense_rle"] == CANONICAL_DENSE_RLE
        assert raster_layer.data["total_pixels"] == 12

    def test_polygon_annotations_still_import_as_polygons(self, tmp_path: Path):
        from darwin.importer.formats import coco_masks

        polygon_annotation = {
            "id": 300,
            "image_id": 1,
            "category_id": 10,
            "iscrowd": 0,
            "segmentation": [[0.0, 0.0, 2.0, 0.0, 2.0, 2.0]],
            "bbox": [0, 0, 2, 2],
            "area": 2,
        }
        coco_file = tmp_path / "coco.json"
        coco_file.write_text(
            json.dumps(
                _coco_json([polygon_annotation, _rle_annotation(100, 20, DOG_RLE)])
            )
        )

        annotation_files = coco_masks.parse_path(coco_file)

        types = [
            a.annotation_class.annotation_type for a in annotation_files[0].annotations
        ]
        assert types.count("polygon") == 1
        assert types.count("mask") == 1
        assert types.count("raster_layer") == 1

    def test_iscrowd_rle_imports_as_mask_instead_of_being_skipped(self, tmp_path: Path):
        from darwin.importer.formats import coco_masks

        coco_file = tmp_path / "coco.json"
        coco_file.write_text(
            json.dumps(_coco_json([_rle_annotation(100, 10, CAT_RLE, iscrowd=1)]))
        )

        annotation_files = coco_masks.parse_path(coco_file)

        types = [
            a.annotation_class.annotation_type for a in annotation_files[0].annotations
        ]
        assert types.count("mask") == 1
        assert types.count("raster_layer") == 1

    def test_empty_dict_segmentation_stays_on_classic_path(self, tmp_path: Path):
        from darwin.importer.formats import coco_masks

        coco_file = tmp_path / "coco.json"
        coco_file.write_text(
            json.dumps(
                _coco_json(
                    [
                        {
                            "id": 400,
                            "image_id": 1,
                            "category_id": 10,
                            "iscrowd": 0,
                            "segmentation": {},
                            "bbox": [1, 1, 2, 2],
                            "area": 4,
                        }
                    ]
                )
            )
        )

        annotation_files = coco_masks.parse_path(coco_file)

        assert annotation_files is not None and len(annotation_files) == 1
        types = [
            a.annotation_class.annotation_type for a in annotation_files[0].annotations
        ]
        assert types == ["bounding_box"]

    def test_registered_with_get_importer(self):
        from darwin.importer import get_importer
        from darwin.importer.formats import coco_masks, supported_formats

        assert "coco_masks" in supported_formats
        assert get_importer("coco_masks") is coco_masks.parse_path

    def test_classic_coco_importer_unchanged(self, tmp_path: Path):
        coco_file = tmp_path / "coco.json"
        coco_file.write_text(
            json.dumps(_coco_json([_rle_annotation(100, 10, CAT_RLE)]))
        )

        annotation_files = coco.parse_path(coco_file)

        types = [
            a.annotation_class.annotation_type for a in annotation_files[0].annotations
        ]
        assert types == ["polygon"]  # classic behavior: RLE polygonized


class TestRoundTrip:
    def test_darwin_masks_survive_coco_round_trip(self, tmp_path: Path):
        darwin_json = {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
            "item": {
                "name": "test.png",
                "path": "/",
                "slots": [{"type": "image", "slot_name": "0", "width": 4, "height": 3}],
            },
            "annotations": [
                {"id": "uuid-1", "name": "cat", "slot_names": ["0"], "mask": {}},
                {"id": "uuid-2", "name": "dog", "slot_names": ["0"], "mask": {}},
                {
                    "id": "uuid-raster",
                    "name": "__raster_layer__",
                    "slot_names": ["0"],
                    "raster_layer": {
                        "dense_rle": CANONICAL_DENSE_RLE,
                        "mask_annotation_ids_mapping": {"uuid-1": 1, "uuid-2": 2},
                        "total_pixels": 12,
                    },
                },
            ],
        }
        src = tmp_path / "annotations"
        out = tmp_path / "out"
        src.mkdir()
        out.mkdir()
        (src / "test.json").write_text(json.dumps(darwin_json))

        # Darwin -> COCO (PR #1177 exporter)
        dt_gen = darwin_exporter.darwin_to_dt_gen(
            list(src.glob("*.json")), split_sequences=False
        )
        coco_exporter.export(dt_gen, out)

        # COCO -> Darwin (coco_masks importer)
        from darwin.importer.formats import coco_masks

        annotation_files = coco_masks.parse_path(out / "output.json")

        assert annotation_files is not None and len(annotation_files) == 1
        annotation_file = annotation_files[0]
        assert annotation_file.filename == "test.png"

        masks = [
            a
            for a in annotation_file.annotations
            if a.annotation_class.annotation_type == "mask"
        ]
        raster_layers = [
            a
            for a in annotation_file.annotations
            if a.annotation_class.annotation_type == "raster_layer"
        ]
        assert len(masks) == 2
        assert len(raster_layers) == 1
        raster_layer = raster_layers[0]

        # The label map survives the full cycle EXACTLY: same dense RLE,
        # same total_pixels, same class->label association.
        assert raster_layer.data["dense_rle"] == CANONICAL_DENSE_RLE
        assert raster_layer.data["total_pixels"] == 12

        mapping = raster_layer.data["mask_annotation_ids_mapping"]
        label_by_class = {
            mask.annotation_class.name: mapping[mask.id] for mask in masks
        }
        assert label_by_class == {"cat": 1, "dog": 2}
