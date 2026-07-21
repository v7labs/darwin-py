import json
from pathlib import Path

import pytest

import darwin.datatypes as dt
from darwin.exporter import exporter
from darwin.exporter.formats import coco


class TestCalculateCategories:
    def test_includes_mask_classes_but_not_raster_layer(self):
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes={
                dt.AnnotationClass("cat", "mask"),
                dt.AnnotationClass("box", "bounding_box"),
                dt.AnnotationClass("__raster_layer__", "raster_layer"),
                dt.AnnotationClass("label", "tag"),
            },
            annotations=[],
            image_height=3,
            image_width=4,
        )

        categories = coco._calculate_categories([annotation_file])

        assert set(categories.keys()) == {"cat", "box"}


class TestBuildAnnotations:
    @pytest.fixture
    def annotation_file(self) -> dt.AnnotationFile:
        return dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=set(),
            annotations=[],
            image_height=1920,
            image_width=1080,
        )

    def test_polygon_include_extras(self, annotation_file: dt.AnnotationFile):
        polygon = dt.Annotation(
            dt.AnnotationClass("polygon_class", "polygon"),
            {"paths": [[{"x": 1, "y": 1}, {"x": 2, "y": 2}, {"x": 1, "y": 2}]]},
            [dt.make_instance_id(1)],
        )

        categories = {"polygon_class": 1}

        assert coco._build_annotation(annotation_file, "test-id", polygon, categories)[
            "extra"
        ] == {"instance_id": 1}

    def test_complex_polygon(self, annotation_file: dt.AnnotationFile):
        polygon = dt.Annotation(
            dt.AnnotationClass("polygon_class", "polygon"),
            {
                "paths": [
                    [{"x": 1, "y": 1}, {"x": 2, "y": 2}, {"x": 1, "y": 2}],
                    [{"x": 3, "y": 3}, {"x": 4, "y": 4}, {"x": 3, "y": 4}],
                ]
            },
            [],
        )

        categories = {"polygon_class": 1}

        annotations = coco._build_annotation(annotation_file, 1, polygon, categories)
        assert annotations["segmentation"]["counts"] == [
            1921,
            2,
            1919,
            1,
            1920,
            2,
            1919,
            1,
            2065915,
        ]
        assert annotations["segmentation"]["size"] == [1920, 1080]

    def test_bounding_boxes_include_extras(self, annotation_file: dt.AnnotationFile):
        bbox = dt.Annotation(
            dt.AnnotationClass("bbox_class", "bounding_box"),
            {"x": 1, "y": 1, "w": 5, "h": 5},
            [dt.make_instance_id(1)],
        )

        categories = {"bbox_class": 1}

        assert coco._build_annotation(annotation_file, "test-id", bbox, categories)[
            "extra"
        ] == {"instance_id": 1}


class TestBuildRasterAnnotations:
    @pytest.fixture
    def raster_annotation_file(self) -> dt.AnnotationFile:
        mask_cat = dt.Annotation(dt.AnnotationClass("cat", "mask"), {}, [], id="uuid-1")
        mask_dog = dt.Annotation(dt.AnnotationClass("dog", "mask"), {}, [], id="uuid-2")
        raster_layer = dt.Annotation(
            dt.AnnotationClass("__raster_layer__", "raster_layer"),
            {
                "dense_rle": [0, 1, 1, 2, 0, 1, 2, 1, 1, 1, 0, 2, 2, 2, 0, 2],
                "mask_annotation_ids_mapping": {"uuid-1": 1, "uuid-2": 2},
                "total_pixels": 12,
            },
            [],
            id="uuid-raster",
        )
        return dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes={
                dt.AnnotationClass("cat", "mask"),
                dt.AnnotationClass("dog", "mask"),
                dt.AnnotationClass("__raster_layer__", "raster_layer"),
            },
            annotations=[mask_cat, mask_dog, raster_layer],
            image_height=3,
            image_width=4,
        )

    def test_exports_one_coco_annotation_per_mask_instance(
        self, raster_annotation_file: dt.AnnotationFile
    ):
        categories = coco._calculate_categories([raster_annotation_file])
        annotations = list(
            coco._build_annotations([raster_annotation_file], categories)
        )

        assert len(annotations) == 2

        cat_ann = next(a for a in annotations if a["category_id"] == categories["cat"])
        assert cat_ann["segmentation"] == {"counts": [3, 2, 1, 1, 5], "size": [3, 4]}
        assert cat_ann["bbox"] == [1, 0, 2, 2]
        assert cat_ann["area"] == 3
        assert cat_ann["iscrowd"] == 0

        dog_ann = next(a for a in annotations if a["category_id"] == categories["dog"])
        assert dog_ann["segmentation"] == {"counts": [1, 2, 2, 1, 6], "size": [3, 4]}
        assert dog_ann["bbox"] == [0, 1, 2, 2]
        assert dog_ann["area"] == 3

    def test_raster_layer_itself_is_not_exported(
        self, raster_annotation_file: dt.AnnotationFile
    ):
        categories = coco._calculate_categories([raster_annotation_file])
        annotations = list(
            coco._build_annotations([raster_annotation_file], categories)
        )

        raster_category_id = coco._calculate_category_id(
            dt.AnnotationClass("__raster_layer__", "raster_layer")
        )
        assert all(a["category_id"] != raster_category_id for a in annotations)

    def test_mask_without_raster_coverage_is_skipped(self):
        orphan_mask = dt.Annotation(
            dt.AnnotationClass("cat", "mask"), {}, [], id="uuid-orphan"
        )
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes={dt.AnnotationClass("cat", "mask")},
            annotations=[orphan_mask],
            image_height=3,
            image_width=4,
        )
        categories = coco._calculate_categories([annotation_file])

        annotations = list(coco._build_annotations([annotation_file], categories))

        assert annotations == []

    def test_full_build_json_populates_categories_and_annotations(
        self, raster_annotation_file: dt.AnnotationFile
    ):
        output = coco._build_json([raster_annotation_file])

        assert {c["name"] for c in output["categories"]} == {"cat", "dog"}
        assert len(output["annotations"]) == 2
        assert len(output["images"]) == 1

    def test_raster_layer_with_odd_length_dense_rle_is_skipped(self):
        mask_cat = dt.Annotation(dt.AnnotationClass("cat", "mask"), {}, [], id="uuid-1")
        raster_layer = dt.Annotation(
            dt.AnnotationClass("__raster_layer__", "raster_layer"),
            {
                "dense_rle": [0, 1, 1, 2, 3],
                "mask_annotation_ids_mapping": {"uuid-1": 1},
                "total_pixels": 12,
            },
            [],
            id="uuid-raster",
        )
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes={
                dt.AnnotationClass("cat", "mask"),
                dt.AnnotationClass("__raster_layer__", "raster_layer"),
            },
            annotations=[mask_cat, raster_layer],
            image_height=3,
            image_width=4,
        )
        categories = coco._calculate_categories([annotation_file])

        annotations = list(coco._build_annotations([annotation_file], categories))

        assert annotations == []

    def test_raster_layer_missing_dense_rle_is_skipped(self):
        mask_cat = dt.Annotation(dt.AnnotationClass("cat", "mask"), {}, [], id="uuid-1")
        raster_layer = dt.Annotation(
            dt.AnnotationClass("__raster_layer__", "raster_layer"),
            {
                "mask_annotation_ids_mapping": {"uuid-1": 1},
                "total_pixels": 12,
            },
            [],
            id="uuid-raster",
        )
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes={
                dt.AnnotationClass("cat", "mask"),
                dt.AnnotationClass("__raster_layer__", "raster_layer"),
            },
            annotations=[mask_cat, raster_layer],
            image_height=3,
            image_width=4,
        )
        categories = coco._calculate_categories([annotation_file])

        annotations = list(coco._build_annotations([annotation_file], categories))

        assert annotations == []


class TestRasterMaskEndToEnd:
    def test_darwin_json_to_coco_export_cycle(self, tmp_path: Path):
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
                        "dense_rle": [0, 1, 1, 2, 0, 1, 2, 1, 1, 1, 0, 2, 2, 2, 0, 2],
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

        dt_gen = exporter.darwin_to_dt_gen(
            list(src.glob("*.json")), split_sequences=False
        )
        coco.export(dt_gen, out)

        result = json.loads((out / "output.json").read_text())

        assert {c["name"] for c in result["categories"]} == {"cat", "dog"}
        assert len(result["annotations"]) == 2
        assert len(result["images"]) == 1
        assert result["images"][0]["height"] == 3
        assert result["images"][0]["width"] == 4

        by_first_count = {
            a["segmentation"]["counts"][0]: a for a in result["annotations"]
        }
        cat_ann = by_first_count[3]
        assert cat_ann["segmentation"] == {"counts": [3, 2, 1, 1, 5], "size": [3, 4]}
        assert cat_ann["bbox"] == [1, 0, 2, 2]
        assert cat_ann["area"] == 3
        assert cat_ann["iscrowd"] == 0

        dog_ann = by_first_count[1]
        assert dog_ann["segmentation"] == {"counts": [1, 2, 2, 1, 6], "size": [3, 4]}
        assert dog_ann["bbox"] == [0, 1, 2, 2]
        assert dog_ann["area"] == 3
