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
    assert r"^[^/].*$".find(v) == -1, "cannot start with a slash"

    return v


class ItemLayoutV1(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.Common.ItemLayoutV1

    # Required fields
    slots: List[str] = Field(...)
    type: Literal["grid", "horizontal", "vertical", "simple"] = Field(...)
    version: Literal[1] = Field(...)


class ItemLayoutV2(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.Common.ItemLayoutV2

    # Required fields
    slots: List[str] = Field(...)
    type: Literal["grid", "horizontal", "vertical", "simple"] = Field(...)
    version: Literal[2] = Field(...)

    # Optional fields
    layout_shape: List[int] = Field(...)


class ItemSlot(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingSlot

    # Required fields
    slot_name: str = Field(...)
    file_name: str = Field(...)
    storage_key: str = Field(...)

    # Optional fields
    as_frames: Optional[bool] = Field(default=False)
    extract_views: Optional[bool] = Field(default=False)
    fps: Optional[ItemFrameRate] = Field(...)
    metadata: Optional[Dict[str, UnknownType]] = Field({})
    tags: Optional[Union[List[str], Dict[str, str]]] = Field([])
    type: Literal["image", "video", "pdf", "dicom"] = Field(...)

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
        if isinstance(v, (int, float)):
            assert v > 0, "fps must be greater than 0"
        if isinstance(v, str):
            assert v == "native", "fps must be 'native' or a number greater than 0"
        return v


class Item(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.NewItem

    # Required fields
    name: str
    slots: List[ItemSlot] = Field(default=[])

    # Optional fields
    path: str
    tags: Optional[Union[List[str], Dict[str, str]]] = Field([])
    layout: Optional[Union[ItemLayoutV1, ItemLayoutV2]] = Field(...)

    @validator("name")
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)
