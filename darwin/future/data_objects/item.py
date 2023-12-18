# @see: GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingItem
from typing import Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import ValidationInfo, field_validator, model_validator

from darwin.datatypes import NumberLike
from darwin.future.data_objects.pydantic_base import DefaultDarwin
from darwin.future.data_objects.typing import UnknownType

ItemFrameRate = Union[NumberLike, Literal["native"]]


def validate_no_slashes(v: UnknownType) -> str:
    assert isinstance(v, str), "Must be a string"
    assert len(v) > 0, "cannot be empty"
    assert "/" not in v, "cannot contain slashes"

    return v


class ItemLayout(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.Common.ItemLayoutV1

    # Required fields
    slots: List[str]
    type: Literal["grid", "horizontal", "vertical", "simple"]
    version: Literal[1, 2]

    # Required only in version 2
    layout_shape: Optional[List[int]] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @field_validator("layout_shape")
    def layout_validator(cls, value: Dict, values: ValidationInfo) -> Dict:
        if not value and values.data.get("version") == 2:
            raise ValueError("layout_shape must be specified for version 2 layouts")

        return value


class ItemSlot(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingSlot

    # Required fields
    slot_name: str
    file_name: str
    fps: Optional[ItemFrameRate] = None

    # Optional fields
    storage_key: Optional[str] = None
    as_frames: Optional[bool] = None
    extract_views: Optional[bool] = None
    metadata: Optional[Dict[str, UnknownType]] = None
    tags: Optional[Union[List[str], Dict[str, str]]] = None
    type: Optional[Literal["image", "video", "pdf", "dicom"]] = None

    @field_validator("slot_name")
    @classmethod
    def validate_slot_name(cls, v: UnknownType) -> str:
        assert isinstance(v, str), "slot_name must be a string"
        assert len(v) > 0, "slot_name cannot be empty"
        return v

    @classmethod
    def validate_fps(cls, values: dict) -> dict:
        value = values.get("fps")

        if value is None:
            values["fps"] = 0
            return values

        assert isinstance(value, (int, float, str)), "fps must be a number or 'native'"
        if isinstance(value, str):
            assert value == "native", "fps must be 'native' or a number greater than 0"
        elif isinstance(value, (int, float)):
            type = values.get("type")
            if type == "image":
                assert value == 0 or value == 1.0, "fps must be '0' or '1.0' for images"
            else:
                assert value >= 0, "fps must be greater than or equal to 0 for videos"

        return values

    @classmethod
    def infer_type(cls, values: Dict[str, UnknownType]) -> Dict[str, UnknownType]:
        file_name = values.get("file_name")

        if file_name is not None:
            # TODO - Review types
            if file_name.endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif")):
                values["type"] = "image"
            elif file_name.endswith(".pdf"):
                values["type"] = "pdf"
            elif file_name.endswith((".dcm", ".nii", ".nii.gz")):
                values["type"] = "dicom"
            elif file_name.endswith((".mp4", ".avi", ".mov", ".wmv", ".mkv")):
                values["type"] = "video"

        return values

    @model_validator(mode="before")
    def root(cls, values: Dict) -> Dict:
        values = cls.infer_type(values)
        values = cls.validate_fps(values)

        return values


class UploadItem(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.NewItem

    # Required fields
    name: str
    slots: List[ItemSlot] = []

    # Optional fields
    description: Optional[str] = None
    path: str = "/"
    tags: Optional[Union[List[str], Dict[str, str]]] = []
    layout: Optional[ItemLayout] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)


class ItemCore(DefaultDarwin):
    # GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.NewItem

    # Required fields
    name: str
    id: UUID
    slots: List[ItemSlot] = []
    path: str = "/"
    dataset_id: int
    processing_status: str

    # Optional fields
    archived: Optional[bool] = False
    priority: Optional[int] = None
    tags: Optional[Union[List[str], Dict[str, str]]] = []
    layout: Optional[ItemLayout] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)


class Folder(DefaultDarwin):
    dataset_id: int
    filtered_item_count: int
    path: str
    unfiltered_item_count: int
