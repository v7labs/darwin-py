from pathlib import Path

import darwin.datatypes as dt
import pytest
from darwin.exporter.formats.darwin_1_0 import _build_json


def describe_build_json():
    def test_empty_annotation_file():
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"), filename="test.json", annotation_classes=[], annotations=[]
        )

        assert _build_json(annotation_file) == {
            'image': {
                'seq': None,
                'width': None,
                'height': None,
                'filename': 'test.json',
                'original_filename': 'test.json',
                'url': None,
                'thumbnail_url': None,
                'path': None,
                'workview_url': None,
            }, 
            'annotations': [], 
            'dataset': 'None'
        }


    def test_dataset_name_field():
        annotation_file = dt.AnnotationFile(
            path=Path("test.json"), filename="test.json", dataset_name="Test dataset", annotation_classes=[], annotations=[]
        )

        assert _build_json(annotation_file) == {
            'image': {
                'seq': None,
                'width': None,
                'height': None,
                'filename': 'test.json',
                'original_filename': 'test.json',
                'url': None,
                'thumbnail_url': None,
                'path': None,
                'workview_url': None,
                }, 
            'annotations': [], 
            'dataset': 'Test dataset'
        }


    def test_complete_annotation_file():
        polygon_path = [{"x": 534.1440000000002,"y": 429.0896},{"x": 531.6440000000002,"y": 428.4196},{"x": 529.8140000000002,"y": 426.5896}]
        annotation_class = dt.AnnotationClass(name="test", annotation_type="polygon")
        annotation = dt.Annotation(annotation_class=annotation_class, data={"path": polygon_path}, subs=[])

        annotation_file = dt.AnnotationFile(
            path=Path("test.json"),
            filename="test.json",
            annotation_classes=[annotation_class],
            annotations=[annotation],
            image_height=1080,
            image_width=1920,
            image_url="https://darwin.v7labs.com/image.jpg",
        )

        assert _build_json(annotation_file) == {'image': {
            'seq': None,
            'width': 1920,
            'height': 1080,
            'filename': 'test.json',
            'original_filename': 'test.json',
            'url': 'https://darwin.v7labs.com/image.jpg',
            'thumbnail_url': None,
            'path': None,
            'workview_url': None,
            }, 
            'annotations': [{'polygon': {'path': polygon_path}, 'name': 'test',
                               'slot_names': []}], 
            'dataset': 'None'
        }


    def test_complex_polygon():
        polygon_path = [
          [
            {
              "x": 230.06,
              "y": 174.04
            },
            {
              "x": 226.39,
              "y": 170.36
            },
            {
              "x": 224.61,
              "y": 166.81
            }
          ],
          [
            {
              "x": 238.98,
              "y": 171.69
            },
            {
              "x": 236.97,
              "y": 174.04
            },
            {
              "x": 238.67,
              "y": 174.04
            }
          ],
          [
            {
              "x": 251.75,
              "y": 169.77
            },
            {
              "x": 251.75,
              "y": 154.34
            },
            {
              "x": 251.08,
              "y": 151.84
            },
            {
              "x": 249.25,
              "y": 150.01
            }
          ]
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

        assert _build_json(annotation_file) == {'image': {
            'seq': None,
            'width': 1920,
            'height': 1080,
            'filename': 'test.json',
            'original_filename': 'test.json',
            'url': 'https://darwin.v7labs.com/image.jpg',
            'thumbnail_url': None,
            'path': None,
            'workview_url': None,
            }, 
            'annotations': [{'complex_polygon': {'path': polygon_path}, 'name': 'test',
                               'slot_names': []}], 
            'dataset': 'None'
        }
