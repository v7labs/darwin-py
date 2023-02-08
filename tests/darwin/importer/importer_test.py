from unittest.mock import patch

import pytest
from rich.theme import Theme

from darwin import datatypes as dt
from darwin.importer.importer import (
    _annotators_or_reviewers_to_payload,
    _console_theme,
    _get_skeleton_name,
    _get_slot_name,
    _handle_annotators,
    _handle_complex_polygon,
    _handle_subs,
    _handle_video_annotations,
    _import_annotations,
    _is_skeleton_class,
    _resolve_annotation_classes,
    build_attribute_lookup,
    find_and_parse,
    get_remote_files,
    import_annotations,
)


@pytest.mark.skip("Not yet implemented.")
def test_build_attribute_lookup() -> None:
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


@pytest.mark.skip("Not yet implemented.")
def test__get_skeleton_name() -> None:
    ...  # TODO: Write this test


@pytest.mark.skip("Not yet implemented.")
def test__handle_subs() -> None:
    ...  # TODO: Write this test - not in current ticket


def test__handle_complex_polygon() -> None:
    assert _handle_complex_polygon({}, {"example": "data", "example2": "data2", "example3": "data3",},) == {
        "example": "data",
        "example2": "data2",
        "example3": "data3",
    }
    assert _handle_complex_polygon(
        dt.Annotation(dt.AnnotationClass("Class", "bbox"), {"paths": [1, 2, 3, 4, 5]}, [], []),
        {"complex_polygon": "test_data"},
    ) == {
        "polygon": {"path": 1, "additional_paths": [2, 3, 4, 5]},
    }


def test__annotators_or_reviewers_to_payload() -> None:
    authors = [
        dt.AnnotationAuthor("John Doe", "john@doe.com"),
        dt.AnnotationAuthor("Jane Doe", "jane@doe.com"),
    ]

    assert _annotators_or_reviewers_to_payload(authors, dt.AnnotationAuthorRole.ANNOTATOR) == [
        {"email": "john@doe.com", "role": "annotator"},
        {"email": "jane@doe.com", "role": "annotator"},
    ]

    assert _annotators_or_reviewers_to_payload(authors, dt.AnnotationAuthorRole.REVIEWER) == [
        {"email": "john@doe.com", "role": "reviewer"},
        {"email": "jane@doe.com", "role": "reviewer"},
    ]


def test__handle_reviewers() -> None:
    with patch("darwin.importer.importer._annotators_or_reviewers_to_payload") as m:
        from darwin.importer.importer import _handle_reviewers

        m.return_value = "test"

        op1 = _handle_reviewers(dt.Annotation("class", {}, [], reviewers=[1, 2, 3]), {}, True)  # type: ignore
        op2 = _handle_reviewers(dt.Annotation("class", {}, [], reviewers=[1, 2, 3]), {}, False)  # type: ignore

        assert op1 == {"reviewers": "test"}
        assert op2 == {}


def test__handle_annotators() -> None:
    with patch("darwin.importer.importer._annotators_or_reviewers_to_payload") as m:
        from darwin.importer.importer import _handle_annotators

        m.return_value = "test"

        op1 = _handle_annotators(dt.Annotation("class", {}, [], annotators=[1, 2, 3]), {}, True)  # type: ignore
        op2 = _handle_annotators(dt.Annotation("class", {}, [], annotators=[1, 2, 3]), {}, False)  # type: ignore

        assert op1 == {"annotators": "test"}
        assert op2 == {}


@pytest.mark.skip("Not yet implemented")  # TODO: Write this test
def test__handle_video_annotations() -> None:
    ...


@pytest.mark.skip("Not yet implemented")  # TODO: Write this test
def test__import_annotations() -> None:
    ...


def test_console_theme() -> None:
    assert isinstance(_console_theme(), Theme)
