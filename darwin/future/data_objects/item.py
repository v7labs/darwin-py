# @see: GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingItem
from typing import Dict, List, Literal, Optional, Union

from pydantic import Field, validator

from darwin.datatypes import NumberLike
from darwin.future.data_objects.pydantic_base import DefaultDarwin
from darwin.future.data_objects.typing import UnknownType

ItemFrameRate = Union[NumberLike, Literal["native"]]


def validate_no_slashes(v: UnknownType) -> str:
    assert isinstance(v, str), "Must be a string"
    assert len(v) > 0, "cannot be empty"
    assert r"^[^/].*$".find(v) != -1, "cannot start with a slash"

    return v


class ItemSlot(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingSlot

    # Required fields
    slot_name: str = Field(..., alias="slotName")
    storage_key: str = Field(..., alias="storageKey")

    # Optional fields
    as_frames: Optional[bool] = Field(None, alias="asFrames")
    extract_views: Optional[bool] = Field(None, alias="extractViews")
    file_name: str = Field(..., alias="fileName")
    fps: Optional[ItemFrameRate] = Field(None, alias="fps")
    metadata: Optional[Dict[str, UnknownType]] = Field({}, alias="metadata")
    tags: Optional[Union[List[str], Dict[str, str]]] = Field(None, alias="tags")
    type: Literal["image", "video", "pdf", "dicom"] = Field(..., alias="type")

    @validator("slot_name")
    def validate_slot_name(cls, v: UnknownType) -> str:
        assert isinstance(v, str), "slot_name must be a string"
        assert len(v) > 0, "slot_name cannot be empty"
        return v

    @validator("storage_key")
    def validate_storage_key(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)

    @validator("fps")
    def validate_fps(cls, v: UnknownType) -> ItemFrameRate:
        assert isinstance(v, (int, float, str)), "fps must be a number or 'native'"
        if isinstance(v, (int, float)):
            assert v > 0, "fps must be greater than 0"
        if isinstance(v, str):
            assert v == "native", "fps must be 'native' or a number greater than 0"
        return v


class Item(DefaultDarwin):
    name: str
    path: str
    slots: List[ItemSlot]

    @validator("name")
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)
