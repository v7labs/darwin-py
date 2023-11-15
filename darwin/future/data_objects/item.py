# @see: GraphotateWeb.Schemas.DatasetsV2.ItemRegistration.ExistingItem
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence, Union
from uuid import UUID

from pydantic import root_validator, validator

from darwin.future.data_objects import NumberLike
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

    @validator("layout_shape", always=True)
    def layout_validator(cls, value: UnknownType, values: Dict) -> Dict:
        if not value and values.get("version") == 2:
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

    @validator("slot_name")
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

    class Config:
        smart_union = True

    @root_validator
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

    @validator("name")
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

    @validator("name")
    def validate_name(cls, v: UnknownType) -> str:
        return validate_no_slashes(v)


class Folder(DefaultDarwin):
    dataset_id: int
    filtered_item_count: int
    path: str
    unfiltered_item_count: int


class ItemUploadStatus(Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ItemUpload(DefaultDarwin):
    id: UUID
    url: str
    status: ItemUploadStatus

    # TODO: members necessary for building an Item object


class ItemCreate(DefaultDarwin):
    """
    ItemCreate

    Payload used to create a new item in a dataset.

    Properties
    ----------
    files : Sequence[PathLike]
        The files to upload.

    files_to_exclude : Optional[Sequence[PathLike]]
        Files to exclude from the upload.

    path : Optional[str]
        The path to upload the files to on the Darwin servers.

    fps : Optional[NumberLike]
        The framerate to upload the files at.

    as_frames : Optional[bool]
        Whether to upload the files as frames.

    extract_views : Optional[bool]
        Whether to extract views from the files.

    preserve_folders : Optional[bool]
        Whether to preserve the folder structure of the files.
    """

    # Required
    files: Sequence[Path]

    # Optional
    files_to_exclude: Optional[Sequence[Path]] = None
    path: Optional[str] = "/"

    fps: Optional[NumberLike] = None
    as_frames: Optional[bool] = False
    extract_views: Optional[bool] = False
    preserve_folders: Optional[bool] = False
    force_slots: Optional[bool] = False

    callback_when_loaded: Optional[Callable[[List[ItemUpload]], None]] = None
    callback_when_complete: Optional[Callable[[List[ItemUpload]], None]] = None
