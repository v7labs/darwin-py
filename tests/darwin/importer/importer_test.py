import json
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock, _patch, patch

import pytest
from rich.theme import Theme

from darwin import datatypes as dt
from darwin.importer.importer import _parse_empty_masks


def root_path(x: str) -> str:
    return f"darwin.importer.importer.{x}"


def mock_pass_through(data: dt.UnknownType) -> dt.UnknownType:
    return data


def patch_factory(module: str) -> _patch:
    return patch(root_path(module))


@pytest.mark.skip("Not yet implemented.")
def test_build_main_annotations_lookup_table() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")  # type: ignore
def test_find_and_parse() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test_build_attribute_lookup() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test_get_remote_files() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test__get_slot_name() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test__resolve_annotation_classes() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test_import_annotations() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test__is_skeleton_class() -> None:
    ...  # TODO: Write this test


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


def test__handle_complex_polygon() -> None:
    from darwin.importer.importer import _handle_complex_polygon

    assert _handle_complex_polygon(
        {},
        {
            "example": "data",
            "example2": "data2",
            "example3": "data3",
        },
    ) == {  # type: ignore
        "example": "data",
        "example2": "data2",
        "example3": "data3",
    }
    assert _handle_complex_polygon(
        dt.Annotation(
            dt.AnnotationClass("Class", "bbox"), {"paths": [1, 2, 3, 4, 5]}, [], []
        ),
        {"complex_polygon": "test_data"},
    ) == {
        "polygon": {"path": 1, "additional_paths": [2, 3, 4, 5]},
    }


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

    with patch_factory("_handle_complex_polygon") as mock_hcp, patch_factory(
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

    with patch_factory("_handle_complex_polygon") as mock_hcp, patch_factory(
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
        Path(__file__).parent.parent / f"data/annotation_raster_layer_data.json"
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
        Path(__file__).parent.parent / f"data/video_annotation_raster_layer_data.json"
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
    with patch_factory("_handle_complex_polygon") as mock_hcp, patch_factory(
        "_handle_reviewers"
    ) as mock_hr, patch_factory("_handle_annotators") as mock_ha, patch_factory(
        "_handle_subs"
    ) as mock_hs, patch_factory(
        "_get_overwrite_value"
    ) as mock_gov, patch_factory(
        "_handle_slot_names"
    ) as mock_hsn:
        from darwin.client import Client
        from darwin.dataset import RemoteDataset
        from darwin.importer.importer import _import_annotations

        mock_client = Mock(Client)
        mock_dataset = Mock(RemoteDataset)

        mock_dataset.version = 2
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

        assert output["annotations"] == assertion["annotations"]
        assert output["overwrite"] == assertion["overwrite"]


def test_console_theme() -> None:
    from darwin.importer.importer import _console_theme

    assert isinstance(_console_theme(), Theme)
