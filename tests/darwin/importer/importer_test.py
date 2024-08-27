import json
import tempfile
from functools import partial
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock, Mock, _patch, patch
from zipfile import ZipFile

import pytest

from darwin import datatypes as dt
from darwin.importer import get_importer
from darwin.importer.importer import (
    _build_attribute_lookup,
    _build_main_annotations_lookup_table,
    _display_slot_warnings_and_errors,
    _find_and_parse,
    _get_annotation_format,
    _get_remote_files,
    _get_slot_names,
    _import_annotations,
    _is_skeleton_class,
    _overwrite_warning,
    _parse_empty_masks,
    _resolve_annotation_classes,
    _verify_slot_annotation_alignment,
)


def root_path(x: str) -> str:
    return f"darwin.importer.importer.{x}"


def mock_pass_through(data: dt.UnknownType) -> dt.UnknownType:
    return data


def patch_factory(module: str) -> _patch:
    return patch(root_path(module))


def test__build_main_annotations_lookup_table() -> None:
    annotation_classes = [
        {"name": "class1", "id": 1, "annotation_types": ["bounding_box", "polygon"]},
        {"name": "class2", "id": 2, "annotation_types": ["ellipse", "keypoint"]},
        {"name": "class3", "id": 3, "annotation_types": ["mask", "raster_layer"]},
        {"name": "class4", "id": 4, "annotation_types": ["unsupported_type"]},
        {"name": "class5", "id": 5, "annotation_types": ["bounding_box", "polygon"]},
    ]

    expected_lookup = {
        "bounding_box": {"class1": 1, "class5": 5},
        "polygon": {"class1": 1, "class5": 5},
        "ellipse": {"class2": 2},
        "keypoint": {"class2": 2},
        "mask": {"class3": 3},
        "raster_layer": {"class3": 3},
    }

    result = _build_main_annotations_lookup_table(annotation_classes)
    assert result == expected_lookup


def test__find_and_parse():
    """
    Ensure that the function doesn't return any None values.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_path = Path(tmpdir) / "v7-darwin-json-v2" / "_find_and_parse"
            importer = get_importer("coco")
            files = _find_and_parse(
                importer=importer,
                file_paths=[annotations_path],
            )
            assert all(isinstance(file, dt.AnnotationFile) for file in files)


def test__build_attribute_lookup() -> None:
    mock_dataset = Mock()
    mock_dataset.fetch_remote_attributes.return_value = [
        {"class_id": "class1", "name": "attribute1", "id": 1},
        {"class_id": "class1", "name": "attribute2", "id": 2},
        {"class_id": "class2", "name": "attribute1", "id": 3},
    ]

    expected_lookup = {
        "class1": {"attribute1": 1, "attribute2": 2},
        "class2": {"attribute1": 3},
    }

    result = _build_attribute_lookup(mock_dataset)
    assert result == expected_lookup


def test__get_remote_files() -> None:
    mock_dataset = Mock()
    mock_dataset.fetch_remote_files.return_value = [
        Mock(full_path="path/to/file1", id="file1_id", layout="layout1"),
        Mock(full_path="path/to/file2", id="file2_id", layout="layout2"),
    ]

    filenames = ["file1", "file2"]
    expected_result = {
        "path/to/file1": {
            "item_id": "file1_id",
            "slot_names": ["slot_name1"],
            "layout": "layout1",
        },
        "path/to/file2": {
            "item_id": "file2_id",
            "slot_names": ["slot_name2"],
            "layout": "layout2",
        },
    }

    with patch("darwin.importer.importer._get_slot_names") as mock_get_slot_names:
        mock_get_slot_names.side_effect = [["slot_name1"], ["slot_name2"]]
        result = _get_remote_files(mock_dataset, filenames)
        assert result == expected_result
        assert mock_get_slot_names.call_count == 2


def test__get_slot_names() -> None:
    mock_remote_file_with_slots_v1 = Mock()
    mock_remote_file_with_slots_v1.layout = {"version": 1}
    mock_remote_file_with_slots_v1.slots = [{"slot_name": "1"}, {"slot_name": "2"}]

    mock_remote_file_without_slots_v1 = Mock()
    mock_remote_file_without_slots_v1.layout = {"version": 1}
    mock_remote_file_without_slots_v1.slots = []

    mock_remote_file_with_slots_v3 = Mock()
    mock_remote_file_with_slots_v3.layout = {"version": 3, "slots_grid": [[["1", "2"]]]}
    mock_remote_file_with_slots_v3.slots = []

    mock_remote_file_without_slots_v3 = Mock()
    mock_remote_file_without_slots_v3.layout = {"version": 3, "slots_grid": [[[]]]}
    mock_remote_file_without_slots_v3.slots = []

    assert _get_slot_names(mock_remote_file_with_slots_v1) == ["1", "2"]
    assert _get_slot_names(mock_remote_file_without_slots_v1) == []

    assert _get_slot_names(mock_remote_file_with_slots_v3) == ["1", "2"]
    assert _get_slot_names(mock_remote_file_without_slots_v3) == []


def test__resolve_annotation_classes() -> None:
    local_annotation_classes = [
        dt.AnnotationClass(name="class1", annotation_type="polygon"),
        dt.AnnotationClass(name="class2", annotation_type="tag"),
        dt.AnnotationClass(name="class3", annotation_type="polygon"),
        dt.AnnotationClass(name="class4", annotation_type="keypoint"),
    ]

    classes_in_dataset = {
        "polygon": {"class1": 1},
        "tag": {"class2": 2},
    }

    classes_in_team = {"polygon": {"class1": 1, "class3": 3}, "tag": {"class2": 2}}

    expected_not_in_dataset = {local_annotation_classes[2]}
    expected_not_in_team = {local_annotation_classes[3]}

    not_in_dataset, not_in_team = _resolve_annotation_classes(
        local_annotation_classes, classes_in_dataset, classes_in_team
    )

    assert not_in_dataset == expected_not_in_dataset
    assert not_in_team == expected_not_in_team


def test_import_annotations() -> None:
    mock_client = Mock()
    mock_dataset = Mock()
    mock_dataset.version = 2
    mock_dataset.team = "test_team"

    remote_classes = {
        "polygon": {"test_class": "123"},
    }
    attributes = {}
    annotations = [
        dt.Annotation(
            dt.AnnotationClass("test_class", "polygon"),
            {"paths": [[1, 2, 3, 4, 5]]},
            [],
            [],
        )
    ]
    default_slot_name = "test_slot"
    append = False
    delete_for_empty = False
    import_annotators = True
    import_reviewers = True
    metadata_path = False

    with patch("darwin.importer.importer._get_annotation_data") as mock_gad, patch(
        "darwin.importer.importer._handle_annotators"
    ) as mock_ha, patch("darwin.importer.importer._handle_reviewers") as mock_hr, patch(
        "darwin.importer.importer._import_properties"
    ) as mock_ip, patch(
        "darwin.importer.importer._get_overwrite_value"
    ) as mock_gov:
        mock_gad.return_value = "test_data"
        mock_ha.return_value = [
            {"email": "annotator1@example.com", "role": "annotator"},
            {"email": "annotator2@example.com", "role": "annotator"},
        ]
        mock_hr.return_value = [
            {"email": "reviewer1@example.com", "role": "reviewer"},
            {"email": "reviewer2@example.com", "role": "reviewer"},
        ]
        mock_ip.return_value = {}
        mock_gov.return_value = "test_append_out"

        errors, success = _import_annotations(
            mock_client,
            "test_id",
            remote_classes,
            attributes,
            annotations,
            default_slot_name,
            mock_dataset,
            append,
            delete_for_empty,
            import_annotators,
            import_reviewers,
            metadata_path,
        )

        assert success == dt.Success.SUCCESS
        assert not errors
        assert mock_dataset.import_annotation.call_count == 1

        payload = mock_dataset.import_annotation.call_args[1]["payload"]
        expected_payload = {
            "annotations": [
                {
                    "annotation_class_id": "123",
                    "data": "test_data",
                    "context_keys": {"slot_names": ["test_slot"]},
                    "id": annotations[0].id,
                    "actors": [
                        {"email": "annotator1@example.com", "role": "annotator"},
                        {"email": "annotator2@example.com", "role": "annotator"},
                        {"email": "reviewer1@example.com", "role": "reviewer"},
                        {"email": "reviewer2@example.com", "role": "reviewer"},
                    ],
                }
            ],
            "overwrite": "test_append_out",
        }

        assert payload == expected_payload


def test__is_skeleton_class() -> None:
    class1 = dt.AnnotationClass(name="class1", annotation_type="skeleton")
    class2 = dt.AnnotationClass(name="class2", annotation_type="polygon")
    class3 = dt.AnnotationClass(
        name="class3", annotation_type="skeleton", annotation_internal_type="skeleton"
    )
    class4 = dt.AnnotationClass(
        name="class4", annotation_type="polygon", annotation_internal_type="polygon"
    )

    assert _is_skeleton_class(class1) is True
    assert _is_skeleton_class(class2) is False
    assert _is_skeleton_class(class3) is True
    assert _is_skeleton_class(class4) is False


def test__get_skeleton_name() -> None:
    from darwin.importer.importer import _get_skeleton_name

    class MockAnnotationClass:
        name: str

        def __init__(self, name: str):
            self.name = name

    assert _get_skeleton_name(MockAnnotationClass("test")) == "test"  # type: ignore
    assert _get_skeleton_name(MockAnnotationClass("test_skeleton")) == "test_skeleton"  # type: ignore


def test_handle_subs() -> None:
    from darwin.importer.importer import _handle_subs

    annotation = dt.Annotation(
        dt.AnnotationClass("class1", "bbox"),
        {},
        [
            dt.SubAnnotation(annotation_type="text", data="some text"),
            dt.SubAnnotation(annotation_type="attributes", data=["attr1", "attr2"]),
            dt.SubAnnotation(annotation_type="instance_id", data="12345"),
            dt.SubAnnotation(annotation_type="other", data={"key": "value"}),
        ],
        [],
        [],
    )

    attributes: dt.DictFreeForm = {"class1": {"attr1": "value1", "attr3": "value3"}}
    annotation_class_id: str = "class1"
    data: dt.DictFreeForm = {}

    expected_result = {
        "text": {"text": "some text"},
        "attributes": {"attributes": ["value1"]},
        "instance_id": {"value": "12345"},
        "other": {"key": "value"},
    }

    result = _handle_subs(annotation, data, annotation_class_id, attributes)
    assert result == expected_result


def test__format_polygon_for_import() -> None:
    from darwin.importer.importer import _format_polygon_for_import

    # Test case when "polygon" key is not in data
    assert _format_polygon_for_import(
        dt.Annotation(
            dt.AnnotationClass("Class", "polygon"), {"paths": [1, 2, 3, 4, 5]}, [], []
        ),
        {"example": "data"},
    ) == {"example": "data"}

    # Test case when "polygon" key is in data and there is more than one path
    assert _format_polygon_for_import(
        dt.Annotation(
            dt.AnnotationClass("Class", "polygon"),
            {"paths": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]},
            [],
            [],
        ),
        {"polygon": {"paths": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]}},
    ) == {"polygon": {"path": [1, 2, 3, 4, 5], "additional_paths": [[6, 7, 8, 9, 10]]}}

    # Test case when "polygon" key is in data and there is only one path
    assert _format_polygon_for_import(
        dt.Annotation(
            dt.AnnotationClass("Class", "polygon"), {"paths": [[1, 2, 3, 4, 5]]}, [], []
        ),
        {"polygon": {"paths": [[1, 2, 3, 4, 5]]}},
    ) == {"polygon": {"path": [1, 2, 3, 4, 5]}}


def test__annotators_or_reviewers_to_payload() -> None:
    from darwin.importer.importer import _annotators_or_reviewers_to_payload

    authors = [
        dt.AnnotationAuthor("John Doe", "john@doe.com"),
        dt.AnnotationAuthor("Jane Doe", "jane@doe.com"),
    ]

    assert _annotators_or_reviewers_to_payload(
        authors, dt.AnnotationAuthorRole.ANNOTATOR
    ) == [
        {"email": "john@doe.com", "role": "annotator"},
        {"email": "jane@doe.com", "role": "annotator"},
    ]

    assert _annotators_or_reviewers_to_payload(
        authors, dt.AnnotationAuthorRole.REVIEWER
    ) == [
        {"email": "john@doe.com", "role": "reviewer"},
        {"email": "jane@doe.com", "role": "reviewer"},
    ]


def test__handle_reviewers() -> None:
    with patch("darwin.importer.importer._annotators_or_reviewers_to_payload") as m:
        from darwin.importer.importer import _handle_reviewers

        m.return_value = "test"

        op1 = _handle_reviewers(dt.Annotation("class", {}, [], reviewers=[1, 2, 3]), True)  # type: ignore
        op2 = _handle_reviewers(dt.Annotation("class", {}, [], reviewers=[1, 2, 3]), False)  # type: ignore

        assert op1 == "test"
        assert op2 == []


def test__handle_annotators() -> None:
    with patch("darwin.importer.importer._annotators_or_reviewers_to_payload") as m:
        from darwin.importer.importer import _handle_annotators

        m.return_value = "test"

        op1 = _handle_annotators(dt.Annotation("class", {}, [], annotators=[1, 2, 3]), True)  # type: ignore
        op2 = _handle_annotators(dt.Annotation("class", {}, [], annotators=[1, 2, 3]), False)  # type: ignore

        assert op1 == "test"
        assert op2 == []


def test__get_annotation_data() -> None:
    annotation_class = dt.AnnotationClass("class", "TEST_TYPE")
    video_annotation_class = dt.AnnotationClass("video_class", "video")

    annotation = dt.Annotation(annotation_class, {}, [], [])
    video_annotation = dt.VideoAnnotation(video_annotation_class, {}, {}, [], False)

    annotation.data = "TEST DATA"

    with patch_factory("_format_polygon_for_import") as mock_hcp, patch_factory(
        "_handle_subs"
    ) as mock_hs, patch.object(
        dt.VideoAnnotation, "get_data", return_value="TEST VIDEO DATA"
    ):
        from darwin.importer.importer import _get_annotation_data

        mock_hcp.return_value = "TEST DATA_HCP"
        mock_hs.return_value = "TEST DATA_HS"

        assert (
            _get_annotation_data(video_annotation, "video_class_id", {})
            == "TEST VIDEO DATA"
        )
        assert _get_annotation_data(annotation, "class_id", {}) == "TEST DATA_HS"

        assert mock_hcp.call_count == 1
        assert mock_hs.call_count == 1

    with patch_factory("_format_polygon_for_import") as mock_hcp, patch_factory(
        "_handle_subs"
    ) as mock_hs:
        from darwin.importer.importer import _get_annotation_data

        mock_hs.return_value = {"TEST_TYPE": "TEST DATA"}

        assert _get_annotation_data(annotation, "class_id", {}) == {
            "TEST_TYPE": "TEST DATA"
        }

        assert mock_hcp.call_args_list[0][0][0] == annotation
        assert mock_hcp.call_args_list[0][0][1] == {"TEST_TYPE": "TEST DATA"}


def __expectation_factory(i: int, slot_names: List[str]) -> dt.Annotation:
    annotation = dt.Annotation(
        dt.AnnotationClass(f"class_{i}", f"TEST_TYPE_{i}"), {}, [], []
    )
    annotation.slot_names.extend(slot_names)

    return annotation


expectations_hsr: List[Tuple[dt.Annotation, int, str, dt.Annotation]] = [
    (
        __expectation_factory(0, []),
        1,
        "default_slot_name",
        __expectation_factory(0, []),
    ),
    (
        __expectation_factory(1, ["slot", "names"]),
        1,
        "default_slot_name",
        __expectation_factory(1, ["slot", "names"]),
    ),
    (
        __expectation_factory(2, []),
        2,
        "default_slot_name",
        __expectation_factory(2, ["default_slot_name"]),
    ),
    (
        __expectation_factory(3, ["slot", "names"]),
        2,
        "default_slot_name",
        __expectation_factory(3, ["slot", "names"]),
    ),
]


@pytest.mark.parametrize(
    "annotation, version, default_slot_name, expected", expectations_hsr
)
def test__handle_slot_names(
    annotation: dt.Annotation,
    version: int,
    default_slot_name: str,
    expected: dt.Annotation,
) -> None:
    from darwin.importer.importer import _handle_slot_names

    assert _handle_slot_names(annotation, version, default_slot_name) == expected


def test_get_overwrite_value() -> None:
    from darwin.importer.importer import _get_overwrite_value

    # Scenario 1: No append value
    assert _get_overwrite_value(True) == "false"

    # Scenario 2: append value
    assert _get_overwrite_value(False) == "true"


@pytest.fixture
def raster_layer_annotations():
    annotation_raster_layer_data = (
        Path(__file__).parent.parent / "data/annotation_raster_layer_data.json"
    )
    with open(annotation_raster_layer_data) as f:
        data = json.load(f)

    return [
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="__raster_layer__",
                annotation_type="raster_layer",
            ),
            data=data,
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="2ef45c58-9556-4a08-b561-61680fd3ba8e",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="CROP:CORN",
                annotation_type="mask",
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="8236a56f-f51b-405e-be02-5c23e0954037",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="CROP:SOYBEAN",
                annotation_type="mask",
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="0835d3c0-2c79-4066-8bd7-41de8bdb695b",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="WEED:UNKNOWN",
                annotation_type="mask",
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="e1beb46e-1343-41ee-a856-6659b89ccd46",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="WEED:GRASS",
                annotation_type="mask",
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="954bbd3e-743f-49b8-b9db-f27e6f7b4ba7",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="WEED:BROADLEAF",
                annotation_type="mask",
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="1a32e512-b135-4307-8aff-46e1ba50f421",
            properties=None,
        ),
        dt.Annotation(
            annotation_class=dt.AnnotationClass(
                name="OBSCURITY:DIRTY_LENS", annotation_type="mask"
            ),
            data={"sparse_rle": None},
            subs=[],
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="20679c9a-4c6e-4ff5-8e41-e4b2e3437c3d",
            properties=None,
        ),
    ]


@pytest.fixture
def raster_layer_video_annotations():
    annotation_raster_layer_data = (
        Path(__file__).parent.parent / "data/video_annotation_raster_layer_data.json"
    )
    with open(annotation_raster_layer_data) as f:
        data = json.load(f)

    return [
        dt.VideoAnnotation(
            annotation_class=dt.AnnotationClass(
                name="__raster_layer__",
                annotation_type="raster_layer",
            ),
            frames={
                0: dt.Annotation(
                    annotation_class=dt.AnnotationClass(
                        name="__raster_layer__",
                        annotation_type="raster_layer",
                    ),
                    data=data,
                    subs=[],
                    slot_names=["0"],
                    annotators=None,
                    reviewers=None,
                    id="220588d7-559d-4797-a465-c0b03fe44a5e",
                    properties=None,
                ),
            },
            keyframes={0: True},
            segments=[[0, 1]],
            interpolated=False,
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="220588d7-559d-4797-a465-c0b03fe44a5e",
            properties=None,
        ),
        dt.VideoAnnotation(
            annotation_class=dt.AnnotationClass(
                name="BAC_mask",
                annotation_type="mask",
            ),
            frames={
                0: dt.Annotation(
                    annotation_class=dt.AnnotationClass(
                        name="BAC_mask",
                        annotation_type="mask",
                    ),
                    data={},
                    subs=[],
                    slot_names=[],
                    annotators=None,
                    reviewers=None,
                    id="ef002bce-99cc-4d9e-bab0-5ef72634ce75",
                    properties=None,
                )
            },
            keyframes={0: True},
            segments=[[0, 1]],
            interpolated=False,
            slot_names=["0"],
            annotators=None,
            reviewers=None,
            id="ef002bce-99cc-4d9e-bab0-5ef72634ce75",
            properties=None,
        ),
    ]


def test__parse_empty_masks(raster_layer_annotations) -> None:
    rl, annotations = raster_layer_annotations[0], raster_layer_annotations[1:]
    rl_dense_rle_ids = None
    rl_dense_rle_ids_frames = None
    for annotation in annotations:
        _parse_empty_masks(annotation, rl, rl_dense_rle_ids, rl_dense_rle_ids_frames)
    assert rl.data["mask_annotation_ids_mapping"] == {
        "0835d3c0-2c79-4066-8bd7-41de8bdb695b": 2
    }


def test__parse_empty_masks_video(raster_layer_video_annotations) -> None:
    rl, annotations = (
        raster_layer_video_annotations[0],
        raster_layer_video_annotations[1:],
    )
    rl_dense_rle_ids = None
    rl_dense_rle_ids_frames = None
    for annotation in annotations:
        _parse_empty_masks(annotation, rl, rl_dense_rle_ids, rl_dense_rle_ids_frames)
    assert rl.frames[0].data["mask_annotation_ids_mapping"] == {
        "ef002bce-99cc-4d9e-bab0-5ef72634ce75": 1
    }


def test__import_annotations() -> None:
    with patch_factory("_format_polygon_for_import") as mock_hcp, patch_factory(
        "_handle_reviewers"
    ) as mock_hr, patch_factory("_handle_annotators") as mock_ha, patch_factory(
        "_handle_subs"
    ) as mock_hs, patch_factory(
        "_get_overwrite_value"
    ) as mock_gov, patch_factory(
        "_handle_slot_names"
    ) as mock_hsn, patch_factory(
        "_import_properties",
    ) as mock_ip:
        from darwin.client import Client
        from darwin.dataset import RemoteDataset
        from darwin.importer.importer import _import_annotations

        mock_client = Mock(Client)
        mock_dataset = Mock(RemoteDataset)

        mock_dataset.version = 2
        mock_dataset.team = "test_team"
        mock_hr.return_value = [
            {"email": "reviewer1@example.com", "role": "reviewer"},
            {"email": "reviewer2@example.com", "role": "reviewer"},
        ]
        mock_ha.return_value = [
            {"email": "annotator1@example.com", "role": "annotator"},
            {"email": "annotator2@example.com", "role": "annotator"},
        ]
        mock_gov.return_value = "test_append_out"
        mock_hs.return_value = "test_sub"
        mock_hsn.return_value = dt.Annotation(
            dt.AnnotationClass("test_class", "bbox"),
            {"paths": [1, 2, 3, 4, 5]},
            [],
            ["test_slot_name"],
        )
        mock_ip.return_value = {}

        annotation = dt.Annotation(
            dt.AnnotationClass("test_class", "bbox"), {"paths": [1, 2, 3, 4, 5]}, [], []
        )

        _import_annotations(
            mock_client,
            "test_id",
            {"bbox": {"test_class": "1337"}},
            {},
            [annotation],
            "test_slot",
            mock_dataset,
            "test_append_in",  # type: ignore
            False,
            "test_import_annotators",  # type: ignore
            "test_import_reviewers",  # type: ignore
            False,
        )

        assert mock_dataset.import_annotation.call_count == 1
        # ! Removed, so this test is now co-dependent on function previously mocked. See IO-841 for future action.
        # assert mock_hva.call_count == 1
        assert mock_hcp.call_count == 1
        assert mock_hr.call_count == 1
        assert mock_ha.call_count == 1
        assert mock_hs.call_count == 1

        assert mock_gov.call_args_list[0][0][0] == "test_append_in"
        assert mock_ha.call_args_list[0][0][1] == "test_import_annotators"
        assert mock_hr.call_args_list[0][0][1] == "test_import_reviewers"

        # Assert handle slot names
        assert mock_hsn.call_args_list[0][0][0] == annotation
        assert mock_hsn.call_args_list[0][0][1] == 2
        assert mock_hsn.call_args_list[0][0][2] == "test_slot"
        assert mock_dataset.import_annotation.call_args_list[0][0][0] == "test_id"

        # Assert assembly of payload
        output = mock_dataset.import_annotation.call_args_list[0][1]["payload"]
        assertion = {
            "annotations": [
                {
                    "annotation_class_id": "1337",
                    "data": "test_sub",
                    "actors": [
                        {"email": "annotator1@example.com", "role": "annotator"},
                        {"email": "annotator2@example.com", "role": "annotator"},
                        {"email": "reviewer1@example.com", "role": "reviewer"},
                        {"email": "reviewer2@example.com", "role": "reviewer"},
                    ],
                    "context_keys": {"slot_names": ["test_slot_name"]},
                }
            ],
            "overwrite": "test_append_out",
        }

        assert (
            output["annotations"][0]["annotation_class_id"]
            == assertion["annotations"][0]["annotation_class_id"]
        )
        assert output["annotations"][0]["data"] == assertion["annotations"][0]["data"]
        assert (
            output["annotations"][0]["actors"] == assertion["annotations"][0]["actors"]
        )
        assert (
            output["annotations"][0]["context_keys"]
            == assertion["annotations"][0]["context_keys"]
        )
        assert output["overwrite"] == assertion["overwrite"]


def test_overwrite_warning_proceeds_with_import():
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "paths": [
                    [
                        {"x": -1, "y": -1},
                        {"x": -1, "y": 1},
                        {"x": 1, "y": 1},
                        {"x": 1, "y": -1},
                        {"x": -1, "y": -1},
                    ]
                ],
                "bounding_box": {"x": -1, "y": -1, "w": 2, "h": 2},
            },
        )
    ]
    client = MagicMock()
    dataset = MagicMock()
    files = [
        dt.AnnotationFile(
            path=Path("/"),
            filename="file1",
            annotation_classes={a.annotation_class for a in annotations},
            annotations=annotations,
            remote_path="/",
        ),
        dt.AnnotationFile(
            path=Path("/"),
            filename="file2",
            annotation_classes={a.annotation_class for a in annotations},
            annotations=annotations,
            remote_path="/",
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "id1",
            "slot_names": ["0"],
            "layout": {"type": "simple", "version": 1, "slots": ["0"]},
        },
        "/file2": {
            "item_id": "id2",
            "slot_names": ["0"],
            "layout": {"type": "simple", "version": 1, "slots": ["0"]},
        },
    }
    console = MagicMock()

    with patch("builtins.input", return_value="y"):
        result = _overwrite_warning(client, dataset, files, remote_files, console)
        assert result is True


def test_overwrite_warning_aborts_import():
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "paths": [
                    [
                        {"x": -1, "y": -1},
                        {"x": -1, "y": 1},
                        {"x": 1, "y": 1},
                        {"x": 1, "y": -1},
                        {"x": -1, "y": -1},
                    ]
                ],
                "bounding_box": {"x": -1, "y": -1, "w": 2, "h": 2},
            },
        )
    ]
    client = MagicMock()
    dataset = MagicMock()
    files = [
        dt.AnnotationFile(
            path=Path("/"),
            filename="file1",
            annotation_classes={a.annotation_class for a in annotations},
            annotations=annotations,
            remote_path="/",
        ),
        dt.AnnotationFile(
            path=Path("/"),
            filename="file2",
            annotation_classes={a.annotation_class for a in annotations},
            annotations=annotations,
            remote_path="/",
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "id1",
            "slot_names": ["0"],
            "layout": {"type": "simple", "version": 1, "slots": ["0"]},
        },
        "/file2": {
            "item_id": "id2",
            "slot_names": ["0"],
            "layout": {"type": "simple", "version": 1, "slots": ["0"]},
        },
    }
    console = MagicMock()

    with patch("builtins.input", return_value="n"):
        result = _overwrite_warning(client, dataset, files, remote_files, console)
        assert result is False


def test__get_annotation_format():
    assert _get_annotation_format(get_importer("coco")) == "coco"
    assert _get_annotation_format(get_importer("csv_tags_video")) == "csv_tags_video"
    assert _get_annotation_format(get_importer("csv_tags")) == "csv_tags"
    assert _get_annotation_format(get_importer("darwin")) == "darwin"
    assert _get_annotation_format(get_importer("dataloop")) == "dataloop"
    assert _get_annotation_format(get_importer("labelbox")) == "labelbox"
    assert _get_annotation_format(get_importer("nifti")) == "nifti"
    assert _get_annotation_format(get_importer("pascal_voc")) == "pascal_voc"
    assert _get_annotation_format(get_importer("superannotate")) == "superannotate"


def test__get_annotation_format_with_partial():
    nifti_importer = get_importer("nifti")
    legacy_nifti_importer = partial(nifti_importer, legacy=True)
    assert _get_annotation_format(legacy_nifti_importer) == "nifti"


def test_no_verify_warning_for_single_slotted_items():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path(filename),
            remote_path="/",
            filename=filename,
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=["0"],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=["0"],
                ),
            ],
        )
        for filename in ["file1", "file2"]
    ]
    remote_files = {
        "/file1": {
            "item_id": "1",
            "slot_names": ["0"],
            "layout": {"type": "grid", "version": 1, "slots": ["0"]},
        },
        "/file2": {
            "item_id": "2",
            "slot_names": ["0"],
            "layout": {"type": "grid", "version": 1, "slots": ["0"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not slot_warnings
    assert not slot_errors


def test_no_slot_name_causes_non_blocking_multi_slotted_warning():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
        dt.AnnotationFile(
            path=Path("file2"),
            remote_path="/",
            filename="file2",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 1, "slots": ["0", "1"]},
        },
        "/file2": {
            "item_id": "124",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 1, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not slot_errors
    assert len(slot_warnings) == 2
    for file in slot_warnings:
        file_warnings = slot_warnings[file]
        assert len(file_warnings) == 2
        for warning in file_warnings:
            assert (
                warning
                == "Annotation imported to multi-slotted item not assigned slot. Uploading to the default slot: 0"
            )


def test_no_slot_name_causes_non_blocking_multi_channeled_warning():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
        dt.AnnotationFile(
            path=Path("file2"),
            remote_path="/",
            filename="file2",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
        "/file2": {
            "item_id": "124",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not slot_errors
    assert len(slot_warnings) == 2
    for file in slot_warnings:
        file_warnings = slot_warnings[file]
        assert len(file_warnings) == 2
        for warning in file_warnings:
            assert (
                warning
                == "Annotation imported to multi-channeled item not assigned a slot. Uploading to the base slot: 0"
            )


def test_non_base_slot_for_channeled_annotations_causes_blocking_warnings():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=["1"],  # Non-base slot
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=["1"],  # Non-base slot
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not local_files
    assert not slot_warnings
    assert len(slot_errors) == 1
    for file in slot_errors:
        file_errors = slot_errors[file]
        assert len(file_errors) == 2
        for error in file_errors:
            assert (
                error
                == "Annotation is linked to slot 1 of the multi-channeled item /file1. Annotations uploaded to multi-channeled items have to be uploaded to the base slot, which for this item is 0."
            )


def test_multiple_non_blocking_and_blocking_errors():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
        dt.AnnotationFile(
            path=Path("file2"),
            remote_path="/",
            filename="file2",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
        dt.AnnotationFile(
            path=Path("file3"),
            remote_path="/",
            filename="file3",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=["1"],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=["1"],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
        "/file2": {
            "item_id": "124",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
        "/file3": {
            "item_id": "125",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert len(slot_warnings) == 2
    assert len(slot_errors) == 1
    for file in slot_warnings:
        file_warnings = slot_warnings[file]
        assert len(file_warnings) == 2
        for warning in file_warnings:
            assert (
                warning
                == "Annotation imported to multi-channeled item not assigned a slot. Uploading to the base slot: 0"
            )
    for file in slot_errors:
        file_errors = slot_errors[file]
        assert len(file_errors) == 2
        for error in file_errors:
            assert (
                error
                == "Annotation is linked to slot 1 of the multi-channeled item /file3. Annotations uploaded to multi-channeled items have to be uploaded to the base slot, which for this item is 0."
            )


def test_blocking_errors_override_non_blocking_errors():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=["1"],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not slot_warnings
    assert len(slot_errors) == 1
    for file in slot_errors:
        file_errors = slot_errors[file]
        assert len(file_errors) == 1
        for error in file_errors:
            assert (
                error
                == "Annotation is linked to slot 1 of the multi-channeled item /file1. Annotations uploaded to multi-channeled items have to be uploaded to the base slot, which for this item is 0."
            )


def test_assign_base_slot_if_missing_from_channel_annotations():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 3, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    assert not slot_errors
    assert len(slot_warnings) == 1
    for file in slot_warnings:
        file_warnings = slot_warnings[file]
        assert len(file_warnings) == 2
        for warning in file_warnings:
            assert (
                warning
                == "Annotation imported to multi-channeled item not assigned a slot. Uploading to the base slot: 0"
            )
    assert local_files[0].annotations[0].slot_names == ["0"]
    assert local_files[0].annotations[1].slot_names == ["0"]


def test_raises_error_for_non_darwin_format_with_warnings():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 1, "slots": ["0", "1"]},
        },
    }
    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )
    console = MagicMock()
    with pytest.raises(TypeError) as excinfo:
        _display_slot_warnings_and_errors(
            slot_errors, slot_warnings, "non-darwin", console
        )
    assert (
        "You are attempting to import annotations to multi-slotted or multi-channeled items using an annotation format that doesn't support them."
        in str(excinfo.value)
    )


def test_does_not_raise_error_for_darwin_format_with_warnings():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1"),
            remote_path="/",
            filename="file1",
            annotation_classes={bounding_box_class},
            annotations=[
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 5, "y": 10, "w": 5, "h": 10},
                    slot_names=[],
                ),
                dt.Annotation(
                    annotation_class=bounding_box_class,
                    data={"x": 15, "y": 20, "w": 15, "h": 20},
                    slot_names=[],
                ),
            ],
        ),
    ]
    remote_files = {
        "/file1": {
            "item_id": "123",
            "slot_names": ["0", "1"],
            "layout": {"type": "grid", "version": 1, "slots": ["0", "1"]},
        },
    }

    local_files, slot_errors, slot_warnings = _verify_slot_annotation_alignment(
        local_files,
        remote_files,
    )

    console = MagicMock()
    _display_slot_warnings_and_errors(slot_errors, slot_warnings, "darwin", console)

    assert not slot_errors
