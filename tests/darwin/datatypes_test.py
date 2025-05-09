import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import pytest

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import (
    AnnotationClass,
    Annotation,
    ObjectStore,
    Point,
    VideoAnnotation,
    make_polygon,
    parse_property_classes,
    split_paths_by_metadata,
)


class TestMakePolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[Point] = [[{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[Point] = [[{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


class TestMakeComplexPolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def assert_annotation_class(annotation, name, type, internal_type=None) -> None:
    assert annotation.annotation_class.name == name
    assert annotation.annotation_class.annotation_type == type
    assert annotation.annotation_class.annotation_internal_type == internal_type


@pytest.mark.parametrize(
    ("filename", "property_class_n", "properties_n"),
    (
        ("metadata.json", 1, [2]),
        ("metadata_nested_properties.json", 3, [0, 0, 1]),
        ("metadata_empty_properties.json", 3, [0, 0, 0]),
    ),
)
def test_parse_properties(filename, property_class_n, properties_n):
    metadata_path = Path(__file__).parent / f"data/{filename}"

    with open(metadata_path) as f:
        metadata = json.load(f)

    property_classes = parse_property_classes(metadata)
    assert len(property_classes) == property_class_n
    assert [
        len(property_class.properties or []) for property_class in property_classes
    ] == properties_n


@pytest.mark.parametrize(
    ("filename", "property_class_n", "properties_n", "is_properties_enabled"),
    (
        ("metadata.json", 1, [2], True),
        ("metadata_nested_properties.json", 3, [0, 0, 1], True),
        ("metadata_empty_properties.json", 0, [], False),
    ),
)
def test_split_paths_by_manifest(
    filename, property_class_n, properties_n, is_properties_enabled
):
    manifest_path = Path(__file__).parent / f"data/{filename}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpdir_v7 = tmpdir / ".v7"
        tmpdir_v7.mkdir(exist_ok=True)
        shutil.copy(manifest_path, tmpdir_v7)

        _path, property_classes = split_paths_by_metadata(tmpdir, filename=filename)

        is_path_file = _path.is_file()
        assert is_path_file == is_properties_enabled
        assert len(property_classes or []) == property_class_n
        assert [
            len(property_class.properties or [])
            for property_class in property_classes or []
        ] == properties_n


class TestObjectStore:
    @pytest.fixture
    def object_store(self):
        return ObjectStore(
            name="test",
            prefix="test_prefix",
            readonly=False,
            provider="aws",
            default=True,
        )

    @pytest.fixture
    def darwin_client(
        darwin_config_path: Path,
        darwin_datasets_path: Path,
        team_slug_darwin_json_v2: str,
    ) -> Client:
        config = Config(darwin_config_path)
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
        config.put(
            ["teams", team_slug_darwin_json_v2, "datasets_dir"],
            str(darwin_datasets_path),
        )
        return Client(config)

    @pytest.fixture
    def remote_dataset_v2(self):
        return RemoteDatasetV2(
            client=self.darwin_client,
            team="test_team",
            name="Test dataset",
            slug="test-dataset",
            dataset_id=1,
        )

    def test_init(self, object_store):
        assert object_store.name == "test"
        assert object_store.prefix == "test_prefix"
        assert object_store.readonly is False
        assert object_store.provider == "aws"
        assert object_store.default is True

    def test_str(self, object_store):
        assert (
            str(object_store)
            == "Storage configuration:\n- Name: test\n- Prefix: test_prefix\n- Readonly: False\n- Provider: aws\n- Default: True"
        )

    def test_repr(self, object_store):
        assert (
            repr(object_store)
            == "ObjectStore(name=test, prefix=test_prefix, readonly=False, provider=aws)"
        )


class TestVideoAnnotationGetData:
    def test_frames_sorted_numerically_for_duplicate_attribute_removal(self):
        annotation_class = AnnotationClass("test", "polygon")
        annotation1 = Annotation(annotation_class, {"data": "frame_1"})
        annotation10 = Annotation(annotation_class, {"data": "frame_10"})
        annotation2 = Annotation(annotation_class, {"data": "frame_2"})
        keyframes = {1: True, 10: True, 2: True}
        segments = [[1, 10]]
        interpolated = True
        slot_names = ["main"]

        # Source frames are out of order
        frames = {
            1: annotation1,
            10: annotation10,
            2: annotation2,
        }

        video_annotation = VideoAnnotation(
            annotation_class,
            frames,
            keyframes,
            segments,
            interpolated,
            slot_names,
        )

        def mock_post_processing(
            annotation: Any, data: Dict[str, Any]
        ) -> Dict[str, Any]:
            if annotation == annotation1:
                data["attributes"] = ["attr1"]
            elif annotation == annotation2:
                data["attributes"] = ["attr1"]  # Same as frame 1, should be removed
            elif annotation == annotation10:
                data["attributes"] = ["attr10"]  # Different from previous frames
            return data

        result = video_annotation.get_data(post_processing=mock_post_processing)

        assert "attributes" in result["frames"][1]
        assert result["frames"][1]["attributes"] == ["attr1"]

        assert (
            "attributes" not in result["frames"][2]
        ), "Duplicate attributes should be removed"

        assert "attributes" in result["frames"][10]
        assert result["frames"][10]["attributes"] == ["attr10"]

    def test_attributes_equality_for_lists_ignores_order(self):
        annotation1 = Annotation(
            AnnotationClass("test", "polygon"), {"data": "frame_1"}
        )
        annotation2 = Annotation(
            AnnotationClass("test", "polygon"), {"data": "frame_2"}
        )
        annotation_class = AnnotationClass("test", "polygon")
        keyframes = {1: True, 2: True}
        segments = [[1, 2]]
        interpolated = True
        slot_names = ["main"]

        frames = {
            1: annotation1,
            2: annotation2,
        }

        video_annotation = VideoAnnotation(
            annotation_class,
            frames,
            keyframes,
            segments,
            interpolated,
            slot_names,
        )

        def mock_post_processing(
            annotation: Any, data: Dict[str, Any]
        ) -> Dict[str, Any]:
            if annotation == annotation1:
                data["attributes"] = ["attr1", "attr2"]
            elif annotation == annotation2:
                data["attributes"] = [
                    "attr2",
                    "attr1",
                ]  # Same elements, different order
            return data

        result = video_annotation.get_data(post_processing=mock_post_processing)

        assert "attributes" in result["frames"][1]
        assert result["frames"][1]["attributes"] == ["attr1", "attr2"]

        assert (
            "attributes" not in result["frames"][2]
        ), "Different order lists should be considered the same set of attributes"

    def test_all_subannotation_present_if_any_are_changed_none_present_otherwise(self):
        """Test all subannotation attributes are correctly processed for changes between frames."""
        annotation_class = AnnotationClass("test", "polygon")
        annotation1 = Annotation(annotation_class, {"data": "frame_1"})
        annotation2 = Annotation(annotation_class, {"data": "frame_2"})
        annotation3 = Annotation(annotation_class, {"data": "frame_3"})
        annotation4 = Annotation(annotation_class, {"data": "frame_4"})

        keyframes = {1: True, 2: True, 3: True, 4: True}
        segments = [[1, 4]]
        interpolated = True
        slot_names = ["main"]

        frames = {
            1: annotation1,
            2: annotation2,
            3: annotation3,
            4: annotation4,
        }

        video_annotation = VideoAnnotation(
            annotation_class,
            frames,
            keyframes,
            segments,
            interpolated,
            slot_names,
        )

        def mock_post_processing(
            annotation: Any, data: Dict[str, Any]
        ) -> Dict[str, Any]:
            # Frame 1: Set initial values for all attributes
            if annotation == annotation1:
                data["text"] = "Initial text"
                data["attributes"] = ["attr1", "attr2"]
                data["instance_id"] = 123

            # Frame 2: Keep the same values (should be removed in output)
            elif annotation == annotation2:
                data["text"] = "Initial text"
                data["attributes"] = ["attr1", "attr2"]
                data["instance_id"] = 123

            # Frame 3: Change only one attribute (text)
            elif annotation == annotation3:
                data["text"] = "Updated text"  # Changed from frame 2
                data["attributes"] = ["attr1", "attr2"]
                data["instance_id"] = 123

            # Frame 4: Keep the same values from frame 3 (should be removed in output)
            elif annotation == annotation4:
                data["text"] = "Updated text"
                data["attributes"] = ["attr1", "attr2"]
                data["instance_id"] = 123

            return data

        result = video_annotation.get_data(post_processing=mock_post_processing)

        # Frame 1: All attributes should be present
        frame1 = result["frames"][1]
        assert frame1["text"] == "Initial text"
        assert frame1["attributes"] == ["attr1", "attr2"]
        assert frame1["instance_id"] == 123

        # Frame 2: All attributes should be removed (unchanged from frame 1)
        frame2 = result["frames"][2]
        assert "text" not in frame2
        assert "attributes" not in frame2
        assert "instance_id" not in frame2

        # Frame 3: All attributes should be present (text changed from frame 2)
        frame3 = result["frames"][3]
        assert frame3["text"] == "Updated text"
        assert frame3["attributes"] == ["attr1", "attr2"]
        assert frame3["instance_id"] == 123

        # Frame 4: All attributes should be removed (unchanged from frame 3)
        frame4 = result["frames"][4]
        assert "text" not in frame4
        assert "attributes" not in frame4
        assert "instance_id" not in frame4
