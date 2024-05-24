from typing import List, Literal, Optional, Tuple

import pytest

from darwin.future.data_objects.item import ItemSlot, validate_no_slashes
from darwin.future.data_objects.typing import UnknownType


def generate_extension_expectations(
    extension: str, expectation: Optional[Literal["image", "video", "pdf", "dicom"]]
) -> List[Tuple[str, Optional[Literal["image", "video", "pdf", "dicom"]]]]:
    """
    Generate a list of tuples of the form (file_name, expectation) where
    """
    return [
        (f"file.{extension}", expectation),
        (f"file.with.dots.{extension}", expectation),
        (f"/file/with/slashes.{extension}", expectation),
        (f"file/with/slashes.{extension}", expectation),
    ]


expectations_list = [
    # Supported images
    *generate_extension_expectations("jpg", "image"),
    *generate_extension_expectations("jpeg", "image"),
    *generate_extension_expectations("png", "image"),
    *generate_extension_expectations("gif", "image"),
    *generate_extension_expectations("bmp", "image"),
    # Supported documents
    *generate_extension_expectations("pdf", "pdf"),
    # Supported medical imaging
    *generate_extension_expectations("dcm", "dicom"),
    *generate_extension_expectations("nii", "dicom"),
    *generate_extension_expectations("nii.gz", "dicom"),
    # Supported videos
    *generate_extension_expectations("mp4", "video"),
    *generate_extension_expectations("avi", "video"),
    *generate_extension_expectations("mov", "video"),
    *generate_extension_expectations("wmv", "video"),
    *generate_extension_expectations("mkv", "video"),
    # Unsupported
    *generate_extension_expectations("unsupported", None),
]


class TestValidateNoSlashes:
    @pytest.mark.parametrize(
        "string", [("validname"), ("valid-name"), ("valid_name_still")]
    )
    def test_happy_paths(self, string: str) -> None:
        assert validate_no_slashes(string) == string

    @pytest.mark.parametrize("string", [(""), (123), ("/invalid_string")])
    def test_sad_paths(self, string: UnknownType) -> None:
        with pytest.raises(AssertionError):
            validate_no_slashes(string)


class TestSlotNameValidator:
    @pytest.mark.parametrize(
        "string", [("validname"), ("valid/name"), ("valid/name/still")]
    )
    def test_happy_paths(self, string: str) -> None:
        assert ItemSlot.validate_slot_name(string) == string

    @pytest.mark.parametrize("string", [(""), (123)])
    def test_sad_paths(self, string: UnknownType) -> None:
        with pytest.raises(AssertionError):
            ItemSlot.validate_slot_name(string)


class TestFpsValidator:
    def test_sets_value_if_absent(self) -> None:
        assert ItemSlot.validate_fps({}) == {"fps": 0}

    @pytest.mark.parametrize("fps", [(0), (1), (1.0), ("native")])
    def test_happy_paths(self, fps: UnknownType) -> None:
        assert ItemSlot.validate_fps({"fps": fps}) == {"fps": fps}

    @pytest.mark.parametrize("fps", [(-1), ("invalid")])
    def test_sad_paths(self, fps: UnknownType) -> None:
        with pytest.raises(AssertionError):
            ItemSlot.validate_fps({"fps": fps})


class TestRootValidator:
    @pytest.mark.parametrize("file_name, expectation", expectations_list)
    def test_happy_paths(self, file_name: str, expectation: str) -> None:
        assert (
            ItemSlot.infer_type({"file_name": file_name}).get("type") == expectation
        ), f"Failed for {file_name}, got {expectation}"
