from pathlib import Path

import darwin.datatypes as dt
from darwin.exporter.formats.darwin_1_0 import _build_json


class TestBuildJson:
    def test_empty_annotation_file(self):
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"), filename="test.json", annotation_classes=[], annotations=[]
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": None,
                "height": None,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": None,
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [],
            "dataset": "None",
        }

    def test_dataset_name_field(self):
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            dataset_name="Test dataset",
            annotation_classes=[],
            annotations=[],
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": None,
                "height": None,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": None,
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [],
            "dataset": "Test dataset",
        }

    def test_complete_annotation_file(self):
        polygon_path = [
            {"x": 534.1440000000002, "y": 429.0896},
            {"x": 531.6440000000002, "y": 428.4196},
            {"x": 529.8140000000002, "y": 426.5896},
        ]
        bounding_box = {"x": 557.66, "y": 428.98, "w": 160.76, "h": 315.3}

        annotation_class = dt.AnnotationClass(name="test", annotation_type="polygon")
        annotation = dt.Annotation(
            annotation_class=annotation_class,
            data={"path": polygon_path, "bounding_box": bounding_box},
            subs=[],
        )

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "polygon": {"path": polygon_path},
                    "name": "test",
                    "slot_names": [],
                    "bounding_box": bounding_box,
                }
            ],
            "dataset": "None",
        }

    def test_complex_polygon(self):
        polygon_path = [
            [
                {"x": 230.06, "y": 174.04},
                {"x": 226.39, "y": 170.36},
                {"x": 224.61, "y": 166.81},
            ],
            [
                {"x": 238.98, "y": 171.69},
                {"x": 236.97, "y": 174.04},
                {"x": 238.67, "y": 174.04},
            ],
            [
                {"x": 251.75, "y": 169.77},
                {"x": 251.75, "y": 154.34},
                {"x": 251.08, "y": 151.84},
                {"x": 249.25, "y": 150.01},
            ],
        ]

        annotation_class = dt.AnnotationClass(name="test", annotation_type="complex_polygon")
        annotation = dt.Annotation(annotation_class=annotation_class, data={"paths": polygon_path}, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "complex_polygon": {"path": polygon_path},
                    "name": "test",
                    "slot_names": [],
                }
            ],
            "dataset": "None",
        }

    def test_polygon_annotation_file_with_bbox(self):
        polygon_path = [
            {"x": 534.1440000000002, "y": 429.0896},
            {"x": 531.6440000000002, "y": 428.4196},
            {"x": 529.8140000000002, "y": 426.5896},
        ]

        bounding_box = {"x": 557.66, "y": 428.98, "w": 160.76, "h": 315.3}

        annotation_class = dt.AnnotationClass(name="test", annotation_type="polygon")
        annotation = dt.Annotation(
            annotation_class=annotation_class,
            data={"path": polygon_path, "bounding_box": bounding_box},
            subs=[],
        )

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "polygon": {"path": polygon_path},
                    "name": "test",
                    "slot_names": [],
                    "bounding_box": bounding_box,
                }
            ],
            "dataset": "None",
        }

    def test_complex_polygon_with_bbox(self):
        polygon_path = [
            [
                {"x": 230.06, "y": 174.04},
                {"x": 226.39, "y": 170.36},
                {"x": 224.61, "y": 166.81},
            ],
            [
                {"x": 238.98, "y": 171.69},
                {"x": 236.97, "y": 174.04},
                {"x": 238.67, "y": 174.04},
            ],
            [
                {"x": 251.75, "y": 169.77},
                {"x": 251.75, "y": 154.34},
                {"x": 251.08, "y": 151.84},
                {"x": 249.25, "y": 150.01},
            ],
        ]

        bounding_box = {"x": 557.66, "y": 428.98, "w": 160.76, "h": 315.3}

        annotation_class = dt.AnnotationClass(name="test", annotation_type="complex_polygon")
        annotation = dt.Annotation(
            annotation_class=annotation_class,
            data={"paths": polygon_path, "bounding_box": bounding_box},
            subs=[],
        )

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "complex_polygon": {"path": polygon_path},
                    "name": "test",
                    "slot_names": [],
                    "bounding_box": bounding_box,
                }
            ],
            "dataset": "None",
        }

    def test_bounding_box(self):
        bounding_box_data = {"x": 100, "y": 150, "w": 50, "h": 30}
        annotation_class = dt.AnnotationClass(name="bbox_test", annotation_type="bounding_box")
        annotation = dt.Annotation(annotation_class=annotation_class, data=bounding_box_data, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "bounding_box": bounding_box_data,
                    "name": "bbox_test",
                    "slot_names": [],
                }
            ],
            "dataset": "None",
        }

    def test_tags(self):
        tag_data = "sample_tag"
        annotation_class = dt.AnnotationClass(name="tag_test", annotation_type="tag")
        annotation = dt.Annotation(annotation_class=annotation_class, data=tag_data, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )
        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [{"tag": {}, "name": "tag_test", "slot_names": []}],
            "dataset": "None",
        }

    def test_polygon_annotation_file_with_bbox(self):
        polygon_path = [
            {"x": 534.1440000000002, "y": 429.0896},
            {"x": 531.6440000000002, "y": 428.4196},
            {"x": 529.8140000000002, "y": 426.5896},
        ]

        bounding_box = {"x": 557.66, "y": 428.98, "w": 160.76, "h": 315.3}

        annotation_class = dt.AnnotationClass(name="test", annotation_type="polygon")
        annotation = dt.Annotation(
            annotation_class=annotation_class, data={"path": polygon_path, "bounding_box": bounding_box}, subs=[]
        )

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {"polygon": {"path": polygon_path}, "name": "test", "slot_names": [], "bounding_box": bounding_box}
            ],
            "dataset": "None",
        }

    def test_complex_polygon_with_bbox(self):
        polygon_path = [
            [
                {"x": 230.06, "y": 174.04},
                {"x": 226.39, "y": 170.36},
                {"x": 224.61, "y": 166.81},
            ],
            [
                {"x": 238.98, "y": 171.69},
                {"x": 236.97, "y": 174.04},
                {"x": 238.67, "y": 174.04},
            ],
            [
                {"x": 251.75, "y": 169.77},
                {"x": 251.75, "y": 154.34},
                {"x": 251.08, "y": 151.84},
                {"x": 249.25, "y": 150.01},
            ],
        ]

        bounding_box = {"x": 557.66, "y": 428.98, "w": 160.76, "h": 315.3}

        annotation_class = dt.AnnotationClass(name="test", annotation_type="complex_polygon")
        annotation = dt.Annotation(
            annotation_class=annotation_class, data={"paths": polygon_path, "bounding_box": bounding_box}, subs=[]
        )

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "complex_polygon": {"path": polygon_path},
                    "name": "test",
                    "slot_names": [],
                    "bounding_box": bounding_box,
                }
            ],
            "dataset": "None",
        }

    def test_bounding_box(self):
        bounding_box_data = {"x": 100, "y": 150, "w": 50, "h": 30}
        annotation_class = dt.AnnotationClass(name="bbox_test", annotation_type="bounding_box")
        annotation = dt.Annotation(annotation_class=annotation_class, data=bounding_box_data, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [
                {
                    "bounding_box": bounding_box_data,
                    "name": "bbox_test",
                    "slot_names": [],
                }
            ],
            "dataset": "None",
        }

    def test_tags(self):
        tag_data = "sample_tag"
        annotation_class = dt.AnnotationClass(name="tag_test", annotation_type="tag")
        annotation = dt.Annotation(annotation_class=annotation_class, data=tag_data, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )
        assert _build_json(annotation_file) == {
            "image": {
                "seq": None,
                "width": 1920,
                "height": 1080,
                "filename": "test.json",
                "original_filename": "test.json",
                "url": "https://darwin.v7labs.com/image.jpg",
                "thumbnail_url": None,
                "path": None,
                "workview_url": None,
            },
            "annotations": [{"tag": {}, "name": "tag_test", "slot_names": []}],
            "dataset": "None",
        }
