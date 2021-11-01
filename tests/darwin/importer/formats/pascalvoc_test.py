from pathlib import Path

import pytest
from darwin.importer.formats.pascalvoc import parse_file


def describe_parse_file():
    @pytest.fixture
    def annotation_path(tmp_path: Path):
        path = tmp_path / "annotation.xml"
        yield path
        path.unlink()

    def it_returns_none_if_path_suffix_is_not_xml():
        path = Path("path/to/file.json")
        assert parse_file(path) is None

    def it_raises_file_not_found_error_if_file_does_not_exist():
        path = Path("path/to/file.xml")

        with pytest.raises(FileNotFoundError):
            parse_file(path)

    def it_raises_value_error_if_filename_tag_not_found(annotation_path: Path):
        annotation_path.write_text("<root></root>")

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find filename element in annotation file"

    def it_raises_value_error_if_filename_tag_has_empty_text(annotation_path: Path):
        annotation_path.write_text("<root><filename> </filename></root>")

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "filename element does not have a text value"

    def it_raises_value_error_if_filename_is_empty(annotation_path: Path):
        annotation_path.write_text("<root><filename></filename></root>")

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "filename element does not have a text value"

    def it_returns_annotation_file_with_empty_annotations_otherwise(annotation_path: Path):
        annotation_path.write_text("<root><filename>image.jpg</filename></root>")

        annotation_file = parse_file(annotation_path)

        assert annotation_file is not None
        assert annotation_file.path == annotation_path
        assert annotation_file.filename == "image.jpg"
        assert not annotation_file.annotation_classes
        assert not annotation_file.annotations
        assert annotation_file.remote_path == "/"

    def it_raises_if_name_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text("<root><filename>image.jpg</filename><object></object></root>")

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find name element in annotation file"

    def it_raises_if_bndbox_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text("<root><filename>image.jpg</filename><object><name>Class</name></object></root>")

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find bndbox element in annotation file"

    def it_raises_if_xmin_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox></bndbox></object></root>"
        )

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find xmin element in annotation file"

    def it_raises_if_xmax_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox><xmin>10</xmin></bndbox></object></root>"
        )

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find xmax element in annotation file"

    def it_raises_if_ymin_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox><xmin>10</xmin><xmax>10</xmax></bndbox></object></root>"
        )

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find ymin element in annotation file"

    def it_raises_if_ymax_tag_not_found_in_object(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox><xmin>10</xmin><xmax>10</xmax><ymin>10</ymin></bndbox></object></root>"
        )

        with pytest.raises(ValueError) as info:
            parse_file(annotation_path)

        assert str(info.value) == "Could not find ymax element in annotation file"

    def it_returns_annotation_file_with_correct_annotations_otherwise(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox><xmin>10</xmin><xmax>10</xmax><ymin>10</ymin><ymax>10</ymax></bndbox></object></root>"
        )

        annotation_file = parse_file(annotation_path)

        assert annotation_file is not None
        assert annotation_file.path == annotation_path
        assert annotation_file.filename == "image.jpg"

        class_ = annotation_file.annotation_classes.pop()
        assert class_.name == "Class"
        assert class_.annotation_type == "bounding_box"

        annotation = annotation_file.annotations.pop()
        assert annotation.annotation_class == class_
        assert annotation.data == {"x": 10, "y": 10, "w": 0, "h": 0}
        assert annotation.subs == []

        assert annotation_file.remote_path == "/"

    def it_returns_annotation_file_with_correct_annotations_with_float_values(annotation_path: Path):
        annotation_path.write_text(
            "<root><filename>image.jpg</filename><object><name>Class</name><bndbox><xmin>10.0</xmin><xmax>10.0</xmax><ymin>10.0</ymin><ymax>10.0</ymax></bndbox></object></root>"
        )

        annotation_file = parse_file(annotation_path)

        assert annotation_file is not None
        assert annotation_file.path == annotation_path
        assert annotation_file.filename == "image.jpg"

        class_ = annotation_file.annotation_classes.pop()
        assert class_.name == "Class"
        assert class_.annotation_type == "bounding_box"

        annotation = annotation_file.annotations.pop()
        assert annotation.annotation_class == class_
        assert annotation.data == {"x": 10, "y": 10, "w": 0, "h": 0}
        assert annotation.subs == []

        assert annotation_file.remote_path == "/"
