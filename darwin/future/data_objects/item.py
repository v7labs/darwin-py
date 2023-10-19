# @see: GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingItem
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from pydantic import root_validator, validator

from darwin.datatypes import NumberLike
from darwin.future.data_objects.pydantic_base import DefaultDarwin
from darwin.future.data_objects.typing import UnknownType

ItemFrameRate = Union[NumberLike, Literal["native"]]


def validate_no_slashes(v: UnknownType) -> str:
    assert isinstance(v, str), "Must be a string"
    assert len(v) > 0, "cannot be empty"
    assert r"^[^/].*$".find(v) == -1, "cannot start with a slash"

    return v


class ItemLayoutV1(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.Common.ItemLayoutV1

    # Required fields
    slots: List[str]
    type: Literal["grid", "horizontal", "vertical", "simple"]
    version: Literal[1]


class ItemLayoutV2(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.Common.ItemLayoutV2

    # Required fields
    slots: List[str]
    type: Literal["grid", "horizontal", "vertical", "simple"]
    version: Literal[2]

    # Optional fields
    layout_shape: Optional[List[int]] = None


class ItemSlot(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingSlot

    # Required fields
    slot_name: str
    file_name: str
    storage_key: str

    # Optional fields
    as_frames: Optional[bool] = None
    extract_views: Optional[bool] = None
    fps: Optional[Union[int, float, Literal["native"]]] = 0
    metadata: Optional[Dict[str, UnknownType]] = None
    tags: Optional[Union[List[str], Dict[str, str]]] = None
    type: Optional[Literal["image", "video", "pdf", "dicom"]] = None

    @validator("slot_name")
    def validate_slot_name(cls, v: UnknownType) -> str:
        assert isinstance(v, str), "slot_name must be a string"
        assert len(v) > 0, "slot_name cannot be empty"
        return v

    @validator("file_name")
    def validate_storage_key(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)

    @validator("fps")
    def validate_fps(cls, v: UnknownType) -> ItemFrameRate:
        assert isinstance(v, (int, float, str)), "fps must be a number or 'native'"
        if isinstance(v, str):
            assert v == "native", "fps must be 'native' or a number greater than 0"
        return v

    class Config:
        smart_union = True

    @root_validator
    def infer_type(cls, values: Dict[str, UnknownType]) -> Dict[str, UnknownType]:
        file_name = values.get("file_name")

        if file_name is not None:
            suffix = Path(file_name).suffix.lower()

            # TODO - Review types
            if suffix in (".jpg", ".jpeg", ".png", ".bmp", ".gif"):
                values["type"] = "image"
            elif suffix == ".pdf":
                values["type"] = "pdf"
            elif suffix in [".dcm", ".nii", ".nii.gz"]:
                values["type"] = "dicom"
            elif suffix in (".mp4", ".avi", ".mov", ".wmv", ".mkv"):
                values["type"] = "video"

            if values["type"] is None:
                values["type"] = "image"

        return values


class Item(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.NewItem

    # Required fields
    name: str
    slots: List[ItemSlot] = []

    # Optional fields
    path: Optional[str] = None
    tags: Optional[Union[List[str], Dict[str, str]]] = []
    layout: Optional[Union[ItemLayoutV1, ItemLayoutV2]] = None

    @validator("name")
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)
