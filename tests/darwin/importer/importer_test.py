import json
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, Mock, _patch, patch
from zipfile import ZipFile

import numpy as np
import pytest
from rich.console import Console

from darwin import datatypes as dt
from darwin.exceptions import RequestEntitySizeExceeded
from darwin.future.data_objects.properties import (
    FullProperty,
    PropertyGranularity,
    PropertyValue,
    SelectedProperty,
)
from darwin.importer import get_importer
from darwin.importer.importer import (
    BASE_URL_LENGTH,
    MAX_URL_LENGTH,
    _assign_item_properties_to_dataset,
    _build_attribute_lookup,
    _build_main_annotations_lookup_table,
    _create_update_item_properties,
    _display_slot_warnings_and_errors,
    _find_and_parse,
    _get_annotation_format,
    _get_remote_files_ready_for_import,
    _get_remote_files_targeted_by_import,
    _get_remote_medical_file_transform_requirements,
    _get_slot_names,
    _import_annotations,
    _import_properties,
    _is_skeleton_class,
    _overwrite_warning,
    _parse_affine,
    _parse_empty_masks,
    _parse_pixdims,
    _parse_plane_map,
    _resolve_annotation_classes,
    _serialize_item_level_properties,
    _split_payloads,
    _verify_slot_annotation_alignment,
    _warn_for_annotations_with_multiple_instance_ids,
    slot_is_handled_by_monai,
    slot_is_medical,
)
from darwin.item import DatasetItem


@pytest.fixture
def mock_client():
    client = Mock()
    client.default_team = "test_team"
    return client


@pytest.fixture
def mock_dataset(mock_client):
    dataset = Mock()
    dataset.team = mock_client.default_team
    dataset.dataset_id = 123456
    return dataset


@pytest.fixture
def mock_console():
    return Mock()


@pytest.fixture
def annotation_class_ids_map():
    return {("test_class", "bbox"): "1337"}


@pytest.fixture
def annotations():
    return [Mock()]


@pytest.fixture
def item_properties():
    return [
        {"name": "prop1", "value": "1"},
        {"name": "prop2", "value": "2"},
        {"name": "prop2", "value": "3"},
    ]


@pytest.fixture
def setup_data(request, multiple_annotations=False):
    granularity = request.param
    client = Mock()
    client.default_team = "test_team"
    team_slug = "test_team"
    annotation_class_ids_map = {("test_class", "polygon"): "123"}
    annotations = [
        dt.Annotation(
            dt.AnnotationClass("test_class", "polygon"),
            {"paths": [[1, 2, 3, 4, 5]]},
            [],
            [],
            id="annotation_id_1",
            properties=[
                SelectedProperty(
                    frame_index=None if granularity == "annotation" else "0",
                    name="existing_property_single_select",
                    type="single_select",
                    value="1",
                ),
                SelectedProperty(
                    frame_index=None if granularity == "annotation" else "0",
                    name="existing_property_multi_select",
                    type="multi_select",
                    value="1",
                ),
                SelectedProperty(
                    frame_index=None if granularity == "annotation" else "1",
                    name="existing_property_multi_select",
                    type="multi_select",
                    value="2",
                ),
            ],
        )
    ]
    if multiple_annotations:
        annotations.append(
            dt.Annotation(
                dt.AnnotationClass("test_class_2", "polygon"),
                {"paths": [[6, 7, 8, 9, 10]]},
                [],
                [],
                id="annotation_id_2",
                properties=[
                    SelectedProperty(
                        frame_index=None if granularity == "annotation" else "0",
                        name="existing_property_single_select",
                        type="single_select",
                        value="1",
                    ),
                    SelectedProperty(
                        frame_index=None if granularity == "annotation" else "0",
                        name="existing_property_multi_select",
                        type="multi_select",
                        value="1",
                    ),
                    SelectedProperty(
                        frame_index=None if granularity == "annotation" else "1",
                        name="existing_property_multi_select",
                        type="multi_select",
                        value="2",
                    ),
                ],
            )
        )
    return client, team_slug, annotation_class_ids_map, annotations


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


def test__get_remote_files_ready_for_import_succeeds() -> None:
    mock_dataset = Mock()
    mock_dataset.fetch_remote_files.return_value = [
        Mock(
            full_path="path/to/file1",
            id="file1_id",
            layout="layout1",
            status="new",
        ),
        Mock(
            full_path="path/to/file2",
            id="file2_id",
            layout="layout2",
            status="annotate",
        ),
        Mock(
            full_path="path/to/file3",
            id="file3_id",
            layout="layout3",
            status="review",
        ),
        Mock(
            full_path="path/to/file4",
            id="file4_id",
            layout="layout4",
            status="complete",
        ),
        Mock(
            full_path="path/to/file5",
            id="file5_id",
            layout="layout5",
            status="archived",
        ),
    ]

    filenames = ["file1", "file2", "file3", "file4"]
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
        "path/to/file3": {
            "item_id": "file3_id",
            "slot_names": ["slot_name3"],
            "layout": "layout3",
        },
        "path/to/file4": {
            "item_id": "file4_id",
            "slot_names": ["slot_name4"],
            "layout": "layout4",
        },
        "path/to/file5": {
            "item_id": "file5_id",
            "slot_names": ["slot_name5"],
            "layout": "layout5",
        },
    }

    with patch("darwin.importer.importer._get_slot_names") as mock_get_slot_names:
        mock_get_slot_names.side_effect = [
            ["slot_name1"],
            ["slot_name2"],
            ["slot_name3"],
            ["slot_name4"],
            ["slot_name5"],
        ]
        result = _get_remote_files_ready_for_import(mock_dataset, filenames)
        assert result == expected_result
        assert mock_get_slot_names.call_count == 5


def test__get_remote_files_ready_for_import_raises_with_statuses_not_ready_for_import() -> (
    None
):
    mock_dataset = Mock()

    mock_dataset.fetch_remote_files.return_value = [
        Mock(full_path="path/to/file2", id="file2_id", layout="layout2", status="error")
    ]
    with pytest.raises(ValueError):
        _get_remote_files_ready_for_import(mock_dataset, ["file2"])

    mock_dataset.fetch_remote_files.return_value = [
        Mock(
            full_path="path/to/file3",
            id="file3_id",
            layout="layout3",
            status="uploading",
        )
    ]
    with pytest.raises(ValueError):
        _get_remote_files_ready_for_import(mock_dataset, ["file3"])

    mock_dataset.fetch_remote_files.return_value = [
        Mock(
            full_path="path/to/file4",
            id="file4_id",
            layout="layout4",
            status="processing",
        )
    ]
    with pytest.raises(ValueError):
        _get_remote_files_ready_for_import(mock_dataset, ["file4"])


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
    item_properties = []
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
            item_properties,
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


def test__handle_subs_empty_attributes() -> None:
    from darwin.importer.importer import _handle_subs

    annotation = dt.Annotation(
        annotation_class=dt.AnnotationClass(
            name="bbox1", annotation_type="bounding_box"
        ),
        data={"x": 451.525, "y": 213.559, "w": 913.22, "h": 538.983},
        subs=[],
        slot_names=[],
        id="a25e4613-718c-4cc8-9170-1bf372853f22",
    )

    initial_data = {
        "bounding_box": {"x": 451.525, "y": 213.559, "w": 913.22, "h": 538.983}
    }

    result = _handle_subs(
        annotation=annotation,
        data=initial_data,
        annotation_class_id="bbox1",
        attributes={},
        include_empty_attributes=True,
    )

    assert result == {
        "bounding_box": {"x": 451.525, "y": 213.559, "w": 913.22, "h": 538.983},
        "attributes": {"attributes": []},
    }


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

        op1 = _handle_reviewers(True, annotation=dt.Annotation("class", {}, [], reviewers=[1, 2, 3]))  # type: ignore
        op2 = _handle_reviewers(False, annotation=dt.Annotation("class", {}, [], reviewers=[1, 2, 3]))  # type: ignore

        assert op1 == "test"
        assert op2 == []


def test__handle_annotators() -> None:
    with patch("darwin.importer.importer._annotators_or_reviewers_to_payload") as m:
        from darwin.importer.importer import _handle_annotators

        m.return_value = "test"

        op1 = _handle_annotators(True, annotation=dt.Annotation("class", {}, [], annotators=[1, 2, 3]))  # type: ignore
        op2 = _handle_annotators(False, annotation=dt.Annotation("class", {}, [], annotators=[1, 2, 3]))  # type: ignore

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


def test__get_annotation_data_video_annotation_with_attributes_that_become_empty() -> (
    None
):
    from darwin.importer.importer import _get_annotation_data

    video_annotation_class = dt.AnnotationClass("video_class", "bounding_box")
    video_annotation = dt.VideoAnnotation(video_annotation_class, {}, {}, [], False)
    video_annotation.keyframes = {1: True, 2: True, 3: True, 4: True}
    video_annotation.frames = {
        1: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[],
            slot_names=[],
        ),
        2: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[
                dt.SubAnnotation(
                    annotation_type="attributes", data=["attribute_1", "attribute_2"]
                )
            ],
            slot_names=[],
        ),
        3: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[
                dt.SubAnnotation(
                    annotation_type="attributes",
                    data=["attribute_1"],
                )
            ],
            slot_names=[],
        ),
        4: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[],
            slot_names=[],
        ),
    }
    attributes = {"video_class_id": {"attribute_1": "id_1", "attribute_2": "id_2"}}
    result = _get_annotation_data(video_annotation, "video_class_id", attributes)
    assert result["frames"][1]["attributes"] == {"attributes": []}
    assert result["frames"][2]["attributes"] == {"attributes": ["id_1", "id_2"]}
    assert result["frames"][3]["attributes"] == {"attributes": ["id_1"]}
    assert result["frames"][4]["attributes"] == {"attributes": []}


def test__get_annotation_data_video_annotation_does_not_wipe_sub_annotations_when_keyframe_is_true() -> (
    None
):
    from darwin.importer.importer import _get_annotation_data

    video_annotation_class = dt.AnnotationClass("video_class", "bounding_box")
    video_annotation = dt.VideoAnnotation(video_annotation_class, {}, {}, [], False)
    video_annotation.keyframes = {1: True, 2: False, 3: True}
    video_annotation.frames = {
        1: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[
                dt.SubAnnotation(
                    annotation_type="attributes",
                    data=["attribute_1", "attribute_2"],
                )
            ],
            slot_names=[],
        ),
        2: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 1, "y": 2, "w": 3, "h": 4},
            subs=[
                dt.SubAnnotation(
                    annotation_type="attributes",
                    data=["attribute_1", "attribute_2"],
                )
            ],
            slot_names=[],
        ),
        3: dt.Annotation(
            annotation_class=video_annotation_class,
            data={"x": 5, "y": 6, "w": 7, "h": 8},
            subs=[
                dt.SubAnnotation(
                    annotation_type="attributes",
                    data=["attribute_1", "attribute_2"],
                )
            ],
            slot_names=[],
        ),
    }
    attributes = {"video_class_id": {"attribute_1": "id_1", "attribute_2": "id_2"}}
    result = _get_annotation_data(video_annotation, "video_class_id", attributes)
    assert result["frames"][1]["attributes"] == {"attributes": ["id_1", "id_2"]}
    assert result["frames"][3]["attributes"] == {"attributes": ["id_1", "id_2"]}


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
            [],
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
        assert mock_ha.call_args_list[0][0][0] == "test_import_annotators"
        assert mock_hr.call_args_list[0][0][0] == "test_import_reviewers"

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


import pytest


@pytest.mark.skip(reason="Skipping while properties refactor is taking place")
class TestImportItemLevelProperties:
    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_properties_from_annotations_no_manifest(
        self,
        mock_client,
        mock_dataset,
        annotations,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = False
            mock_get_team_props.side_effect = [
                ({}, {}),
                ({}, {}),
                ({}, {}),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="multi_select",
                            description="property-created-during-annotation-import",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="property-created-during-annotation-import",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="2"),
                                PropertyValue(type="string", value="3"),
                            ],
                        ),
                    },
                ),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties=item_properties,
                client=mock_client,
                annotations=annotations,
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][0:2]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][0:2]

            assert len(create_properties_first_call) == 0
            assert len(update_properties_first_call) == 0
            assert len(create_properties_second_call) == 2
            assert len(update_properties_second_call) == 0

            assert create_properties_second_call[0] == FullProperty(
                name="prop1",
                type="multi_select",
                description="property-created-during-annotation-import",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                ],
            )
            assert create_properties_second_call[1] == FullProperty(
                name="prop2",
                type="multi_select",
                description="property-created-during-annotation-import",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="2"),
                    PropertyValue(type="string", value="3"),
                ],
            )

    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_properties_from_manifest_no_annotations(
        self,
        mock_client,
        mock_dataset,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = Path(
                "darwin/future/tests/data/.v7/metadata_with_item_level_properties.json"
            )
            mock_get_team_props.side_effect = [
                ({}, {}),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties={},
                client=mock_client,
                annotations=[],
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][2:4]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][2:4]

            assert len(create_properties_first_call) == 2
            assert len(update_properties_first_call) == 0
            assert len(create_properties_second_call) == 0
            assert len(update_properties_second_call) == 0

            assert create_properties_first_call[0] == FullProperty(
                name="prop1",
                type="single_select",
                description="",
                required=True,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert create_properties_first_call[1] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                    PropertyValue(type="string", value="2"),
                ],
            )

    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_properties_from_manifest_and_annotations(
        self,
        mock_client,
        mock_dataset,
        annotations,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = Path(
                "darwin/future/tests/data/.v7/metadata_with_item_level_properties.json"
            )
            mock_get_team_props.side_effect = [
                ({}, {}),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                                PropertyValue(type="string", value="3"),
                            ],
                        ),
                    },
                ),
                ({}, {}),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties=item_properties,
                client=mock_client,
                annotations=annotations,
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][2:4]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][2:4]

            assert len(create_properties_first_call) == 2
            assert len(update_properties_first_call) == 0
            assert len(create_properties_second_call) == 0
            assert len(update_properties_second_call) == 1

            assert create_properties_first_call[0] == FullProperty(
                name="prop1",
                type="single_select",
                description="",
                required=True,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert create_properties_first_call[1] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert update_properties_second_call[0] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="3"),
                ],
            )

    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_property_values_from_manifest_no_annotations(
        self,
        mock_client,
        mock_dataset,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = Path(
                "darwin/future/tests/data/.v7/metadata_with_item_level_properties.json"
            )
            mock_get_team_props.side_effect = [
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties={},
                client=mock_client,
                annotations=[],
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][2:4]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][2:4]

            assert len(create_properties_first_call) == 0
            assert len(update_properties_first_call) == 2
            assert len(create_properties_second_call) == 0
            assert len(update_properties_second_call) == 0

            assert update_properties_first_call[0] == FullProperty(
                name="prop1",
                type="single_select",
                description="",
                required=True,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert update_properties_first_call[1] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="1"),
                ],
            )

    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_property_values_from_annotations_no_manifest(
        self,
        mock_client,
        mock_dataset,
        annotations,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = False
            mock_get_team_props.side_effect = [
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                                PropertyValue(type="string", value="3"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                                PropertyValue(type="string", value="3"),
                            ],
                        ),
                    },
                ),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties=item_properties,
                client=mock_client,
                annotations=annotations,
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][2:4]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][2:4]

            assert len(create_properties_first_call) == 0
            assert len(update_properties_first_call) == 0
            assert len(create_properties_second_call) == 0
            assert len(update_properties_second_call) == 1

            assert update_properties_second_call[0] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="3"),
                ],
            )

    @pytest.mark.skip(reason="Skipping while properties refactor is taking place")
    def test_import_properties_creates_missing_item_level_property_values_from_manifest_and_annotations(
        self,
        mock_client,
        mock_dataset,
        annotations,
        annotation_class_ids_map,
        item_properties,
    ):
        with patch(
            "darwin.importer.importer._get_team_properties_annotation_lookup"
        ) as mock_get_team_props, patch(
            "darwin.importer.importer._create_update_item_properties"
        ) as mock_create_update_props:
            metadata_path = Path(
                "darwin/future/tests/data/.v7/metadata_with_item_level_properties.json"
            )
            mock_get_team_props.side_effect = [
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                    },
                ),
                (
                    {},
                    {
                        "prop1": FullProperty(
                            name="prop1",
                            type="single_select",
                            description="",
                            required=True,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                            ],
                        ),
                        "prop2": FullProperty(
                            name="prop2",
                            type="multi_select",
                            description="",
                            required=False,
                            slug="test_team",
                            dataset_ids=[],
                            granularity=PropertyGranularity("item"),
                            property_values=[
                                PropertyValue(type="string", value="1"),
                                PropertyValue(type="string", value="2"),
                                PropertyValue(type="string", value="3"),
                            ],
                        ),
                    },
                ),
            ]
            mock_create_update_props.side_effect = _create_update_item_properties

            _import_properties(
                metadata_path=metadata_path,
                item_properties=item_properties,
                client=mock_client,
                annotations=annotations,
                annotation_class_ids_map=annotation_class_ids_map,
                dataset=mock_dataset,
            )

            (
                create_properties_first_call,
                update_properties_first_call,
            ) = mock_create_update_props.call_args_list[0][0][2:4]
            (
                create_properties_second_call,
                update_properties_second_call,
            ) = mock_create_update_props.call_args_list[1][0][2:4]

            assert len(create_properties_first_call) == 0
            assert len(update_properties_first_call) == 2
            assert len(create_properties_second_call) == 0
            assert len(update_properties_second_call) == 1

            assert update_properties_first_call[0] == FullProperty(
                name="prop1",
                type="single_select",
                description="",
                required=True,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert update_properties_first_call[1] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="2"),
                ],
            )
            assert update_properties_second_call[0] == FullProperty(
                name="prop2",
                type="multi_select",
                description="",
                required=False,
                slug="test_team",
                granularity=PropertyGranularity("item"),
                property_values=[
                    PropertyValue(type="string", value="3"),
                ],
            )


def test__assign_item_properties_to_dataset(mock_client, mock_dataset, mock_console):
    item_properties = [
        {"name": "prop1", "value": "1"},
        {"name": "prop2", "value": "2"},
    ]

    team_item_properties_lookup = {
        "prop1": FullProperty(
            name="prop1",
            type="single_select",
            description="",
            required=True,
            slug="test_team",
            dataset_ids=[123],
            granularity=PropertyGranularity("item"),
            property_values=[
                PropertyValue(type="string", value="1"),
            ],
        ),
        "prop2": FullProperty(
            name="prop2",
            type="multi_select",
            description="",
            required=False,
            slug="test_team",
            dataset_ids=[456],
            granularity=PropertyGranularity("item"),
            property_values=[
                PropertyValue(type="string", value="2"),
            ],
        ),
    }

    with patch(
        "darwin.importer.importer._get_team_properties_annotation_lookup"
    ) as mock_get_team_props, patch.object(
        mock_client, "update_property"
    ) as mock_update_property:
        mock_get_team_props.return_value = ({}, team_item_properties_lookup)

        _assign_item_properties_to_dataset(
            item_properties,
            team_item_properties_lookup,
            mock_client,
            mock_dataset,
            mock_console,
        )

        assert mock_update_property.call_count == 2

        updated_props = [call[0][1] for call in mock_update_property.call_args_list]

        for updated_prop in updated_props:
            assert mock_dataset.dataset_id in updated_prop.dataset_ids
            assert 123456 in updated_prop.dataset_ids
            if 123 in updated_prop.dataset_ids:
                assert "prop1" == updated_prop.name
            elif 456 in updated_prop.dataset_ids:
                assert "prop2" == updated_prop.name


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


def test_does_not_raise_error_for_nifti_format_with_warnings():
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
    _display_slot_warnings_and_errors(slot_errors, slot_warnings, "nifti", console)

    assert not slot_errors


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["section"], indirect=True)
def test_import_existing_section_level_property_values_without_manifest(
    mock_get_team_properties,
    mock_dataset,
    setup_data,
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_1"),
            ],
            granularity=PropertyGranularity.section,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
                PropertyValue(value="2", id="property_value_id_3"),
            ],
            granularity=PropertyGranularity.section,
        ),
    }, {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_1"),
            ],
            granularity=PropertyGranularity.section,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
                PropertyValue(value="2", id="property_value_id_3"),
            ],
            granularity=PropertyGranularity.section,
        ),
    }
    metadata_path = False
    result = _import_properties(
        metadata_path, [], client, annotations, annotation_class_ids_map, mock_dataset
    )
    assert result["annotation_id_1"]["0"]["property_id_1"] == {
        "property_value_id_1",
    }
    assert result["annotation_id_1"]["0"]["property_id_2"] == {
        "property_value_id_2",
    }
    assert result["annotation_id_1"]["1"]["property_id_2"] == {
        "property_value_id_3",
    }


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["section"], indirect=True)
def test_import_new_section_level_property_values_with_manifest(
    mock_get_team_properties,
    mock_dataset,
    setup_data,
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[],
            granularity=PropertyGranularity.section,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
            ],
            granularity=PropertyGranularity.section,
        ),
    }, {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[PropertyValue(value="1", id="property_value_id_1")],
            granularity=PropertyGranularity.section,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
                PropertyValue(value="2", id="property_value_id_3"),
            ],
            granularity=PropertyGranularity.section,
        ),
    }
    metadata_path = (
        Path(__file__).parents[1]
        / "data"
        / "metadata_missing_section_property_values.json"
    )
    with patch.object(client, "update_property") as mock_update_property:
        result = _import_properties(
            metadata_path,
            [],
            client,
            annotations,
            annotation_class_ids_map,
            mock_dataset,
        )
        assert result["annotation_id_1"]["0"]["property_id_2"] == {
            "property_value_id_2",
        }
        assert mock_update_property.call_args_list[0].kwargs["params"] == FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            description="property-updated-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="1", color="rgba(255,46,0,1.0)"),
            ],
            granularity=PropertyGranularity.section,
        )
        assert mock_update_property.call_args_list[1].kwargs["params"] == FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            description="property-updated-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="2", color="rgba(255,199,0,1.0)"),
            ],
            granularity=PropertyGranularity.section,
        )


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["section"], indirect=True)
def test_import_identical_properties_to_different_classes(
    mock_get_team_properties, mock_dataset, setup_data
):
    client, team_slug, _, _ = setup_data
    # This test requires 2 annotation classes
    annotation_class_ids_map = {
        ("test_class_1", "polygon"): 1,
        ("test_class_2", "polygon"): 2,
    }
    annotations = [
        (
            dt.Annotation(
                dt.AnnotationClass("test_class_1", "polygon"),
                {"paths": [[1, 2, 3, 4, 5]]},
                [],
                [],
                id="1",
                properties=[
                    SelectedProperty(
                        frame_index="0",
                        name="existing_property_single_select",
                        type="single_select",
                        value="1",
                    ),
                ],
            )
        ),
        (
            dt.Annotation(
                dt.AnnotationClass("test_class_2", "polygon"),
                {"paths": [[1, 2, 3, 4, 5]]},
                [],
                [],
                id="2",
                properties=[
                    SelectedProperty(
                        frame_index="0",
                        name="existing_property_single_select",
                        type="single_select",
                        value="1",
                    ),
                ],
            )
        ),
    ]
    mock_get_team_properties.return_value = {}, {}
    metadata_path = (
        Path(__file__).parents[1]
        / "data"
        / "metadata_identical_properties_different_classes.json"
    )
    with patch.object(client, "create_property") as mock_create_property:
        mock_create_property.side_effect = [
            FullProperty(
                name="existing_property_single_select",
                id="prop_id_1",
                type="single_select",
                required=False,
                description="property-created-during-annotation-import",
                annotation_class_id=1,
                slug="test_team",
                property_values=[
                    PropertyValue(
                        value="1", color="rgba(255,46,0,1.0)", id="prop_val_id_1"
                    ),
                ],
                granularity=PropertyGranularity.section,
            ),
            FullProperty(
                name="existing_property_single_select",
                id="prop_id_2",
                type="single_select",
                required=False,
                description="property-created-during-annotation-import",
                annotation_class_id=2,
                slug="test_team",
                property_values=[
                    PropertyValue(
                        value="1", color="rgba(255,46,0,1.0)", id="prop_val_id_2"
                    ),
                ],
                granularity=PropertyGranularity.section,
            ),
        ]
        annotation_property_map = _import_properties(
            metadata_path,
            [],
            client,
            annotations,
            annotation_class_ids_map,
            mock_dataset,
        )
        assert annotation_property_map["1"]["0"]["prop_id_1"] == {"prop_val_id_1"}
        assert annotation_property_map["2"]["0"]["prop_id_2"] == {"prop_val_id_2"}


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["section"], indirect=True)
def test_import_new_section_level_properties_with_manifest(
    mock_get_team_properties,
    mock_dataset,
    setup_data,
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = {}, {}
    metadata_path = (
        Path(__file__).parents[1]
        / "data"
        / "metadata_missing_section_property_values.json"
    )
    with patch.object(client, "create_property") as mock_create_property:
        _import_properties(
            metadata_path,
            [],
            client,
            annotations,
            annotation_class_ids_map,
            mock_dataset,
        )
        assert mock_create_property.call_args_list[0].kwargs["params"] == FullProperty(
            id=None,
            position=None,
            name="existing_property_single_select",
            type="single_select",
            required=False,
            description="property-created-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            team_id=None,
            property_values=[
                PropertyValue(value="1", color="rgba(255,46,0,1.0)"),
            ],
            options=None,
            granularity=PropertyGranularity.section,
        )
        assert mock_create_property.call_args_list[1].kwargs["params"] == FullProperty(
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            description="property-created-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="1", color="rgba(173,255,0,1.0)"),
                PropertyValue(value="2", color="rgba(255,199,0,1.0)"),
            ],
            granularity=PropertyGranularity.section,
        )


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["annotation"], indirect=True)
def test_import_existing_annotation_level_property_values_without_manifest(
    mock_get_team_properties,
    mock_dataset,
    setup_data,
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_1"),
            ],
            granularity=PropertyGranularity.annotation,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
                PropertyValue(value="2", id="property_value_id_3"),
            ],
            granularity=PropertyGranularity.annotation,
        ),
    }, {
        ("existing_property_single_select", 123): FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_1"),
            ],
            granularity=PropertyGranularity.annotation,
        ),
        ("existing_property_multi_select", 123): FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            property_values=[
                PropertyValue(value="1", id="property_value_id_2"),
                PropertyValue(value="2", id="property_value_id_3"),
            ],
            granularity=PropertyGranularity.annotation,
        ),
    }
    metadata_path = False
    result = _import_properties(
        metadata_path, [], client, annotations, annotation_class_ids_map, mock_dataset
    )
    assert result["annotation_id_1"]["None"]["property_id_1"] == {
        "property_value_id_1",
    }
    assert result["annotation_id_1"]["None"]["property_id_2"] == {
        "property_value_id_2",
        "property_value_id_3",
    }


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["annotation"], indirect=True)
def test_import_new_annotation_level_property_values_with_manifest(
    mock_get_team_properties, setup_data, mock_dataset
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = (
        {
            ("existing_property_single_select", 123): FullProperty(
                id="property_id_1",
                name="existing_property_single_select",
                type="single_select",
                required=False,
                property_values=[],
                granularity=PropertyGranularity.annotation,
            ),
            ("existing_property_multi_select", 123): FullProperty(
                id="property_id_2",
                name="existing_property_multi_select",
                type="multi_select",
                required=False,
                property_values=[
                    PropertyValue(value="1", id="property_value_id_2"),
                ],
                granularity=PropertyGranularity.annotation,
            ),
        },
        {
            ("existing_property_single_select", 123): FullProperty(
                id="property_id_1",
                name="existing_property_single_select",
                type="single_select",
                required=False,
                property_values=[PropertyValue(value="1", id="property_value_id_1")],
                granularity=PropertyGranularity.annotation,
            ),
            ("existing_property_multi_select", 123): FullProperty(
                id="property_id_2",
                name="existing_property_multi_select",
                type="multi_select",
                required=False,
                property_values=[
                    PropertyValue(value="1", id="property_value_id_2"),
                    PropertyValue(value="2", id="property_value_id_3"),
                ],
                granularity=PropertyGranularity.annotation,
            ),
        },
    )
    metadata_path = (
        Path(__file__).parents[1]
        / "data"
        / "metadata_missing_annotation_property_values.json"
    )
    with patch.object(client, "update_property") as mock_update_property:
        result = _import_properties(
            metadata_path,
            [],
            client,
            annotations,
            annotation_class_ids_map,
            mock_dataset,
        )
        assert result["annotation_id_1"]["None"]["property_id_2"] == {
            "property_value_id_2",
        }
        assert mock_update_property.call_args_list[0].kwargs["params"] == FullProperty(
            id="property_id_1",
            name="existing_property_single_select",
            type="single_select",
            required=False,
            description="property-updated-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="1", color="rgba(255,46,0,1.0)"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        assert mock_update_property.call_args_list[1].kwargs["params"] == FullProperty(
            id="property_id_2",
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            description="property-updated-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="2", color="rgba(255,199,0,1.0)"),
            ],
            granularity=PropertyGranularity.annotation,
        )


@patch("darwin.importer.importer._get_team_properties_annotation_lookup")
@pytest.mark.parametrize("setup_data", ["annotation"], indirect=True)
def test_import_new_annotation_level_properties_with_manifest(
    mock_get_team_properties,
    mock_dataset,
    setup_data,
):
    client, team_slug, annotation_class_ids_map, annotations = setup_data
    mock_get_team_properties.return_value = {}, {}
    metadata_path = (
        Path(__file__).parents[1]
        / "data"
        / "metadata_missing_annotation_property_values.json"
    )
    with patch.object(client, "create_property") as mock_create_property:
        _import_properties(
            metadata_path,
            [],
            client,
            annotations,
            annotation_class_ids_map,
            mock_dataset,
        )
        assert mock_create_property.call_args_list[0].kwargs["params"] == FullProperty(
            name="existing_property_single_select",
            type="single_select",
            required=False,
            description="property-created-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="1", color="rgba(255,46,0,1.0)"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        assert mock_create_property.call_args_list[1].kwargs["params"] == FullProperty(
            name="existing_property_multi_select",
            type="multi_select",
            required=False,
            description="property-created-during-annotation-import",
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(value="1", color="rgba(173,255,0,1.0)"),
                PropertyValue(value="2", color="rgba(255,199,0,1.0)"),
            ],
            granularity=PropertyGranularity.annotation,
        )


def test_no_instance_id_warning_with_no_video_annotations():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1.json"),
            is_video=False,
            annotations=[],
            filename="file1",
            annotation_classes={bounding_box_class},
        ),
        dt.AnnotationFile(
            path=Path("file2.json"),
            is_video=False,
            annotations=[],
            filename="file2",
            annotation_classes={bounding_box_class},
        ),
    ]
    console = MagicMock()
    _warn_for_annotations_with_multiple_instance_ids(local_files, console)
    console.print.assert_not_called()


def test_warning_with_multiple_files_with_multi_instance_id_annotations():
    bounding_box_class = dt.AnnotationClass(
        name="class1", annotation_type="bounding_box"
    )
    annotation1 = dt.VideoAnnotation(
        annotation_class=bounding_box_class,
        frames={
            0: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 5, "y": 10, "w": 5, "h": 10},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="1"),
                ],
            ),
            1: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 15, "y": 20, "w": 15, "h": 20},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="2"),
                ],
            ),
            2: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 25, "y": 30, "w": 25, "h": 30},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="3"),
                ],
            ),
        },
        keyframes={0: True, 1: False, 2: True},
        segments=[[0, 2]],
        interpolated=False,
    )
    annotation2 = dt.VideoAnnotation(
        annotation_class=bounding_box_class,
        frames={
            0: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 5, "y": 10, "w": 5, "h": 10},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="1"),
                ],
            ),
            1: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 15, "y": 20, "w": 15, "h": 20},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="2"),
                ],
            ),
            2: dt.Annotation(
                annotation_class=dt.AnnotationClass(
                    name="class1", annotation_type="bounding_box"
                ),
                data={"x": 25, "y": 30, "w": 25, "h": 30},
                subs=[
                    dt.SubAnnotation(annotation_type="instance_id", data="3"),
                ],
            ),
        },
        keyframes={0: True, 1: False, 2: True},
        segments=[[0, 2]],
        interpolated=False,
    )
    local_files = [
        dt.AnnotationFile(
            path=Path("file1.json"),
            is_video=True,
            annotations=[annotation1],
            filename="file1",
            annotation_classes={bounding_box_class},
        ),
        dt.AnnotationFile(
            path=Path("file2.json"),
            is_video=True,
            annotations=[annotation2],
            filename="file2",
            annotation_classes={bounding_box_class},
        ),
    ]
    console = MagicMock()
    _warn_for_annotations_with_multiple_instance_ids(local_files, console)
    console.print.assert_called()
    assert (
        console.print.call_count == 3
    )  # One for the warning message, two for the file details


def test_serialize_item_level_properties_empty_input():
    """Test that empty input returns empty list"""
    result = _serialize_item_level_properties([], Mock(), Mock(), False, False)
    assert result == []


def test_serialize_item_level_properties_single_select():
    """Test serialization of single select property"""
    # Setup
    client = Mock()
    dataset = Mock(team="test_team")

    property_value_id = "123"
    property_id = "456"

    # Mock property value
    property_value = PropertyValue(id=property_value_id, value="option1")

    # Mock full property
    full_property = FullProperty(
        id=property_id,
        name="test_property",
        type="single_select",
        property_values=[property_value],
        required=False,
        granularity=PropertyGranularity("item"),
    )

    # Mock team properties lookup
    mock_lookup_response = ({}, {"test_property": full_property})

    with patch(
        "darwin.importer.importer._get_team_properties_annotation_lookup",
        return_value=mock_lookup_response,
    ):
        result = _serialize_item_level_properties(
            [{"name": "test_property", "value": "option1"}],
            client,
            dataset,
            False,
            False,
        )

    expected = [
        {"actors": [], "property_id": property_id, "value": {"id": property_value_id}}
    ]

    assert result == expected


def test_serialize_item_level_properties_text():
    """Test serialization of text property"""
    # Setup
    client = Mock()
    dataset = Mock(team="test_team")

    property_id = "789"

    # Mock full property
    full_property = FullProperty(
        id=property_id,
        name="text_property",
        type="text",
        required=False,
        granularity=PropertyGranularity("item"),
    )

    # Mock team properties lookup
    mock_lookup_response = ({}, {"text_property": full_property})

    with patch(
        "darwin.importer.importer._get_team_properties_annotation_lookup",
        return_value=mock_lookup_response,
    ):
        result = _serialize_item_level_properties(
            [{"name": "text_property", "value": "some text"}],
            client,
            dataset,
            False,
            False,
        )

    expected = [
        {"actors": [], "property_id": property_id, "value": {"text": "some text"}}
    ]

    assert result == expected


def test_serialize_item_level_properties_with_actors():
    """Test serialization with annotators and reviewers"""
    # Setup
    client = Mock()
    dataset = Mock(team="test_team")

    property_id = "789"

    # Mock full property
    full_property = FullProperty(
        id=property_id,
        name="text_property",
        type="text",
        required=False,
        granularity=PropertyGranularity("item"),
    )

    # Mock team properties lookup
    mock_lookup_response = ({}, {"text_property": full_property})

    # Mock annotator and reviewer handlers
    mock_annotator = {"email": "annotator@test.com", "role": "annotator"}
    mock_reviewer = {"email": "reviewer@test.com", "role": "reviewer"}

    with patch(
        "darwin.importer.importer._get_team_properties_annotation_lookup",
        return_value=mock_lookup_response,
    ), patch(
        "darwin.importer.importer._handle_annotators", return_value=[mock_annotator]
    ), patch(
        "darwin.importer.importer._handle_reviewers", return_value=[mock_reviewer]
    ):
        result = _serialize_item_level_properties(
            [{"name": "text_property", "value": "some text"}],
            client,
            dataset,
            True,
            True,
        )

    expected = [
        {
            "actors": [mock_annotator, mock_reviewer],
            "property_id": property_id,
            "value": {"text": "some text"},
        }
    ]

    assert result == expected


def test_serialize_item_level_properties_multiple_properties():
    """Test serialization of multiple properties"""
    # Setup
    client = Mock()
    dataset = Mock(team="test_team")

    # Mock properties
    text_property = FullProperty(
        id="123",
        name="text_property",
        type="text",
        required=False,
        granularity=PropertyGranularity("item"),
    )

    select_property_value = PropertyValue(id="456", value="option1")
    select_property = FullProperty(
        id="789",
        name="select_property",
        type="single_select",
        property_values=[select_property_value],
        required=False,
        granularity=PropertyGranularity("item"),
    )

    # Mock team properties lookup
    mock_lookup_response = (
        {},
        {"text_property": text_property, "select_property": select_property},
    )

    with patch(
        "darwin.importer.importer._get_team_properties_annotation_lookup",
        return_value=mock_lookup_response,
    ):
        result = _serialize_item_level_properties(
            [
                {"name": "text_property", "value": "some text"},
                {"name": "select_property", "value": "option1"},
            ],
            client,
            dataset,
            False,
            False,
        )

    expected = [
        {"actors": [], "property_id": "123", "value": {"text": "some text"}},
        {"actors": [], "property_id": "789", "value": {"id": "456"}},
    ]

    assert result == expected


def test__split_payloads_returns_multiple_payloads():
    payload = {
        "annotations": [
            {"id": "annotation_1", "data": "data1"},
            {"id": "annotation_2", "data": "data2"},
            {"id": "annotation_3", "data": "data3"},
        ],
        "overwrite": True,
    }
    max_payload_size = 100

    result = _split_payloads(payload, max_payload_size)

    assert len(result) == 3
    assert result[0]["annotations"] == [payload["annotations"][0]]
    assert result[1]["annotations"] == [payload["annotations"][1]]
    assert result[2]["annotations"] == [payload["annotations"][2]]


def test__split_payloads_with_annotation_exceeding_size_limit():
    payload = {
        "annotations": [
            {"id": "annotation_1", "data": "a" * 1000},  # Large annotation
            {"id": "annotation_2", "data": "data2"},
        ],
        "overwrite": True,
    }
    max_payload_size = 100

    with pytest.raises(
        ValueError,
        match="One or more annotations exceed the maximum allowed size",
    ):
        _split_payloads(payload, max_payload_size)


def test__split_payloads_overwrites_on_first_payload_and_appends_on_the_rest():
    """
    When importing annotations, we need to respect the overwrite behaviour defined by the user.
    However, if we need to split payloads, all payloads after the first will have to be appended
    """
    payload = {
        "annotations": [
            {"id": "annotation_1", "data": "data1"},
            {"id": "annotation_2", "data": "data2"},
            {"id": "annotation_3", "data": "data3"},
        ],
        "overwrite": True,
    }
    max_payload_size = 100

    result = _split_payloads(payload, max_payload_size)

    assert len(result) == 3
    assert result[0]["overwrite"]
    assert not result[1]["overwrite"]
    assert not result[2]["overwrite"]


def test__get_remote_files_targeted_by_import_success() -> None:
    """Test successful case where files are found remotely."""
    mock_dataset = Mock()
    mock_console = Mock()

    mock_remote_file1 = Mock(full_path="/path/to/file1.json")
    mock_remote_file2 = Mock(full_path="/path/to/file2.json")

    mock_dataset.fetch_remote_files.return_value = [
        mock_remote_file1,
        mock_remote_file2,
    ]

    def mock_importer(path: Path) -> List[dt.AnnotationFile]:
        file_num = int(path.stem.replace("file", ""))
        mock_file = Mock(
            spec=dt.AnnotationFile,
            filename=f"file{file_num}.json",
            full_path=f"/path/to/file{file_num}.json",
        )
        return [mock_file]

    result = _get_remote_files_targeted_by_import(
        importer=mock_importer,
        file_paths=[Path("file1.json"), Path("file2.json")],
        dataset=mock_dataset,
        console=mock_console,
    )

    assert len(result) == 2
    assert result[0] == mock_remote_file1
    assert result[1] == mock_remote_file2
    mock_dataset.fetch_remote_files.assert_called_once()


def test__get_remote_files_targeted_by_import_no_files_parsed() -> None:
    """Test error case when no files can be parsed."""
    mock_dataset = Mock()
    mock_console = Mock()

    def mock_importer(path: Path) -> Optional[List[dt.AnnotationFile]]:
        return None

    with pytest.raises(ValueError, match="Not able to parse any files."):
        _get_remote_files_targeted_by_import(
            importer=mock_importer,
            file_paths=[Path("file1.json")],
            dataset=mock_dataset,
            console=mock_console,
        )


def test__get_remote_files_targeted_by_import_url_too_long() -> None:
    """Test that files that would cause URL length to exceed limits are handled appropriately."""
    mock_dataset = Mock()
    mock_console = Mock()

    very_long_filename = "a" * (MAX_URL_LENGTH - BASE_URL_LENGTH + 10) + ".json"

    def mock_importer(path: Path) -> List[dt.AnnotationFile]:
        mock_file = Mock(
            spec=dt.AnnotationFile,
            filename=very_long_filename,
            full_path=f"/path/to/{very_long_filename}",
        )
        return [mock_file]

    mock_dataset.fetch_remote_files.side_effect = RequestEntitySizeExceeded()

    with pytest.raises(RequestEntitySizeExceeded):
        _get_remote_files_targeted_by_import(
            importer=mock_importer,
            file_paths=[Path("file1.json")],
            dataset=mock_dataset,
            console=mock_console,
        )

    mock_dataset.fetch_remote_files.assert_called_once_with(
        filters={"item_names": [very_long_filename]}
    )


def test__get_remote_medical_file_transform_requirements_empty_list():
    """Test that empty input list returns empty dictionaries"""
    mock_console = MagicMock(spec=Console)
    remote_files: List[DatasetItem] = []
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}


def test__get_remote_medical_file_transform_requirements_no_slots():
    """Test that files with no slots are handled correctly"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = None
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}


def test__get_remote_medical_file_transform_requirements_non_medical_slots():
    """Test that files with non-medical slots are handled correctly"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = [{"slot_name": "slot1", "metadata": {}}]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}


def test__get_remote_medical_file_transform_requirements_monai_axial():
    """Test MONAI-handled medical slots with AXIAL plane"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "handler": "MONAI",
                    "plane_map": {"slot1": "AXIAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {
        Path("/path/to/file"): {"slot1": ([1.0, 2.0, 3.0], "AXIAL")}
    }


def test__get_remote_medical_file_transform_requirements_monai_coronal():
    """Test MONAI-handled medical slots with CORONAL plane"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "handler": "MONAI",
                    "plane_map": {"slot1": "CORONAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {
        Path("/path/to/file"): {"slot1": ([1.0, 2.0, 3.0], "CORONAL")}
    }


def test__get_remote_medical_file_transform_requirements_monai_sagittal():
    """Test MONAI-handled medical slots with SAGGITAL plane"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "handler": "MONAI",
                    "plane_map": {"slot1": "SAGITTAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {
        Path("/path/to/file"): {"slot1": ([1.0, 2.0, 3.0], "SAGITTAL")}
    }


def test__get_remote_medical_file_transform_requirements_legacy_nifti():
    """Test legacy NifTI scaling"""
    mock_console = MagicMock(spec=Console)
    mock_file = MagicMock(spec=DatasetItem)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "affine": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                    "plane_map": {"slot1": "AXIAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )
    assert pixdims_and_primary_planes == {
        Path("/path/to/file"): {"slot1": ([1.0, 2.0, 3.0], "AXIAL")}
    }
    assert Path("/path/to/file") in legacy_scaling
    assert "slot1" in legacy_scaling[Path("/path/to/file")]
    assert legacy_scaling[Path("/path/to/file")]["slot1"].shape == (4, 4)
    assert (
        legacy_scaling[Path("/path/to/file")]["slot1"]
        == np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64
        )
    ).all()


def test__get_remote_medical_file_transform_requirements_mixed():
    """Test mixed case with both MONAI and legacy NifTI files"""
    mock_console = MagicMock(spec=Console)
    mock_file1 = MagicMock(spec=DatasetItem)
    mock_file1.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "handler": "MONAI",
                    "plane_map": {"slot1": "AXIAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file1.full_path = "/path/to/file1"

    mock_file2 = MagicMock(spec=DatasetItem)
    mock_file2.slots = [
        {
            "slot_name": "slot2",
            "metadata": {
                "medical": {
                    "affine": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                    "pixdims": [1.0, 2.0, 3.0],
                    "plane_map": {"slot2": "AXIAL"},
                }
            },
        }
    ]
    mock_file2.full_path = "/path/to/file2"

    remote_files: List[DatasetItem] = [mock_file1, mock_file2]
    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    assert pixdims_and_primary_planes == {
        Path("/path/to/file1"): {"slot1": ([1.0, 2.0, 3.0], "AXIAL")},
        Path("/path/to/file2"): {"slot2": ([1.0, 2.0, 3.0], "AXIAL")},
    }
    assert Path("/path/to/file2") in legacy_scaling
    assert "slot2" in legacy_scaling[Path("/path/to/file2")]
    assert legacy_scaling[Path("/path/to/file2")]["slot2"].shape == (4, 4)
    assert (
        legacy_scaling[Path("/path/to/file2")]["slot2"]
        == np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64
        )
    ).all()


def test__get_remote_medical_file_transform_requirements_missing_plane_map():
    """Test handling of missing plane_map in medical metadata"""
    mock_file = MagicMock(spec=DatasetItem)
    mock_console = MagicMock(spec=Console)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "pixdims": [1.0, 2.0, 3.0],
                    # plane_map is missing
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}
    mock_console.print.assert_called_once_with(
        "Missing plane_map for slot slot1 in file /path/to/file", style="warning"
    )


def test__get_remote_medical_file_transform_requirements_missing_pixdims():
    """Test handling of missing pixdims in medical metadata"""
    mock_file = MagicMock(spec=DatasetItem)
    mock_console = MagicMock(spec=Console)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "plane_map": {"slot1": "AXIAL"},
                    # pixdims is missing
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}
    mock_console.print.assert_called_once_with(
        "Missing pixdims for slot slot1 in file /path/to/file", style="warning"
    )


def test__get_remote_medical_file_transform_requirements_none_pixdims():
    """Test handling of None pixdims in medical metadata"""
    mock_file = MagicMock(spec=DatasetItem)
    mock_console = MagicMock(spec=Console)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {"medical": {"plane_map": {"slot1": "AXIAL"}, "pixdims": None}},
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}
    mock_console.print.assert_called_once_with(
        "Missing pixdims for slot slot1 in file /path/to/file", style="warning"
    )


def test__get_remote_medical_file_transform_requirements_invalid_pixdims():
    """Test handling of invalid pixdims format"""
    mock_file = MagicMock(spec=DatasetItem)
    mock_console = MagicMock(spec=Console)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "plane_map": {"slot1": "AXIAL"},
                    "pixdims": ["not", "valid", "numbers"],
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {}
    mock_console.print.assert_called_once_with(
        "Invalid pixdims format for slot slot1 in file /path/to/file", style="warning"
    )


def test__get_remote_medical_file_transform_requirements_invalid_affine():
    """Test handling of invalid affine matrix format"""
    mock_file = MagicMock(spec=DatasetItem)
    mock_console = MagicMock(spec=Console)
    mock_file.slots = [
        {
            "slot_name": "slot1",
            "metadata": {
                "medical": {
                    "plane_map": {"slot1": "AXIAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                    "affine": "not a valid matrix",
                }
            },
        }
    ]
    mock_file.full_path = "/path/to/file"
    remote_files: List[DatasetItem] = [mock_file]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    # Should still have pixdims even though affine is invalid
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {
        Path("/path/to/file"): {"slot1": ([1.0, 2.0, 3.0], "AXIAL")}
    }
    mock_console.print.assert_called_once_with(
        "Invalid affine matrix format for slot slot1 in file /path/to/file",
        style="warning",
    )


def test__get_remote_medical_file_transform_requirements_multiple_slots_partial_failure():
    """Test handling of multiple slots where some succeed and others fail"""
    mock_console = MagicMock(spec=Console)

    # Create two mock files with different full paths
    mock_file_valid = MagicMock(spec=DatasetItem)
    mock_file_valid.slots = [
        {
            "slot_name": "valid_slot",
            "metadata": {
                "medical": {
                    "plane_map": {"valid_slot": "AXIAL"},
                    "pixdims": [1.0, 2.0, 3.0],
                }
            },
        }
    ]
    mock_file_valid.full_path = "/path/to/valid_file"

    mock_file_invalid = MagicMock(spec=DatasetItem)
    mock_file_invalid.slots = [
        {
            "slot_name": "invalid_slot",
            "metadata": {
                "medical": {
                    "plane_map": {"invalid_slot": "AXIAL"},
                    "pixdims": ["not", "valid", "numbers"],
                }
            },
        }
    ]
    mock_file_invalid.full_path = "/path/to/invalid_file"

    remote_files: List[DatasetItem] = [mock_file_valid, mock_file_invalid]

    legacy_scaling, pixdims_and_primary_planes = (
        _get_remote_medical_file_transform_requirements(remote_files, mock_console)
    )

    # Should have data for the valid slot but not the invalid one
    assert legacy_scaling == {}
    assert pixdims_and_primary_planes == {
        Path("/path/to/valid_file"): {"valid_slot": ([1.0, 2.0, 3.0], "AXIAL")}
    }
    mock_console.print.assert_called_once_with(
        "Invalid pixdims format for slot invalid_slot in file /path/to/invalid_file",
        style="warning",
    )


@pytest.fixture
def valid_medical_metadata():
    return {
        "plane_map": {"slot1": "axial"},
        "pixdims": ["1.0", "2.0", "3.0"],
        "affine": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
    }


def test_parse_plane_map_valid(valid_medical_metadata):
    mock_console = MagicMock(spec=Console)
    result = _parse_plane_map(
        valid_medical_metadata, "slot1", "test/file.nii", mock_console
    )
    assert result == "axial"


def test_parse_plane_map_missing_plane_map():
    mock_console = MagicMock(spec=Console)
    result = _parse_plane_map({}, "slot1", "test/file.nii", mock_console)
    assert result is None


def test_parse_plane_map_invalid_type():
    mock_console = MagicMock(spec=Console)
    result = _parse_plane_map(
        {"plane_map": "not_a_dict"}, "slot1", "test/file.nii", mock_console
    )
    assert result is None


def test_parse_plane_map_missing_slot():
    mock_console = MagicMock(spec=Console)
    result = _parse_plane_map(
        {"plane_map": {"other_slot": "axial"}}, "slot1", "test/file.nii", mock_console
    )
    assert result is None


def test_parse_pixdims_valid(valid_medical_metadata):
    mock_console = MagicMock(spec=Console)
    result = _parse_pixdims(
        valid_medical_metadata, "slot1", "test/file.nii", mock_console
    )
    assert result == [1.0, 2.0, 3.0]


def test_parse_pixdims_missing():
    mock_console = MagicMock(spec=Console)
    result = _parse_pixdims({}, "slot1", "test/file.nii", mock_console)
    assert result is None


def test_parse_pixdims_empty():
    mock_console = MagicMock(spec=Console)
    result = _parse_pixdims({"pixdims": []}, "slot1", "test/file.nii", mock_console)
    assert result is None


def test_parse_pixdims_invalid_values():
    mock_console = MagicMock(spec=Console)
    result = _parse_pixdims(
        {"pixdims": ["not", "valid", "numbers"]}, "slot1", "test/file.nii", mock_console
    )
    assert result is None


def test_parse_affine_valid(valid_medical_metadata):
    mock_console = MagicMock(spec=Console)
    result = _parse_affine(
        valid_medical_metadata, "slot1", "test/file.nii", mock_console
    )
    expected = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    assert np.array_equal(result, expected)


def test_parse_affine_missing():
    mock_console = MagicMock(spec=Console)
    result = _parse_affine({}, "slot1", "test/file.nii", mock_console)
    assert result is None


def test_parse_affine_invalid_values():
    mock_console = MagicMock(spec=Console)
    invalid_affine = {"affine": "not_a_matrix"}
    result = _parse_affine(invalid_affine, "slot1", "test/file.nii", mock_console)
    assert result is None


def test_slot_is_medical():
    medical_slot = {"metadata": {"medical": {"some": "data"}}}
    non_medical_slot = {"metadata": {}}
    empty_slot = {}

    assert slot_is_medical(medical_slot) is True
    assert slot_is_medical(non_medical_slot) is False
    assert slot_is_medical(empty_slot) is False


def test_slot_is_handled_by_monai():
    monai_slot = {"metadata": {"medical": {"handler": "MONAI"}}}
    non_monai_slot = {"metadata": {"medical": {"handler": "other"}}}
    no_handler_slot = {"metadata": {"medical": {}}}
    empty_slot = {}

    assert slot_is_handled_by_monai(monai_slot) is True
    assert slot_is_handled_by_monai(non_monai_slot) is False
    assert slot_is_handled_by_monai(no_handler_slot) is False
    assert slot_is_handled_by_monai(empty_slot) is False
