import json
from collections import namedtuple
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple
from uuid import UUID

import requests

from darwin.datatypes import JSONType

ConfigValues = namedtuple("ConfigValues", ["server", "api_key", "team_slug"])


@dataclass
class E2EAnnotation:
    annotation_data: JSONType


@dataclass
class E2EAnnotationClass:
    name: str
    type: Literal["bbox", "polygon"]
    id: int


class E2EItemLevelProperty:
    def __init__(self, name: str, dataset_ids: List[int], type: str, id: str):
        self.name = name
        self.dataset_ids = dataset_ids
        self.type = type
        self.id = id


@dataclass
class E2EItem(Exception):
    name: str
    id: UUID
    path: str
    file_name: str
    slot_name: str
    annotations: List[E2EAnnotation]

    def add_annotation(self, annotation: E2EAnnotation) -> None:
        self.annotations.append(annotation)


@dataclass
class E2EDataset:
    id: int
    name: str
    slug: str
    items: List[E2EItem]
    directory: Optional[str] = None

    def __init__(
        self, id: int, name: str, slug: Optional[str], directory: Optional[str] = None
    ) -> None:
        self.id = id
        self.name = name
        self.slug = slug or name.lower().replace(" ", "_")
        self.items = []
        self.directory = directory

    def add_item(self, item: E2EItem) -> None:
        self.items.append(item)

    def register_read_only_items(
        self,
        config_values: ConfigValues,
        item_type: str = "single_slotted",
        files_in_flat_structure: bool = False,
    ) -> None:
        """
        Registers a set of images from an external bucket in the dataset in a read-only fashion:

        Useful for creating dataset to test `pull` or `import` operations on without having to wait for items to finish processing
        """
        payload = get_read_only_registration_payload(
            item_type,
            dataset_slug=self.slug,
            files_in_flat_structure=files_in_flat_structure,
        )
        api_key = config_values.api_key
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"ApiKey {api_key}",
        }
        response = requests.post(
            f"{config_values.server}/api/v2/teams/{config_values.team_slug}/items/register_existing_readonly",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        for item in json.loads(response.text)["items"]:
            self.add_item(
                E2EItem(
                    name=item["name"],
                    id=item["id"],
                    path=item["path"],
                    file_name=item["name"],
                    slot_name=item["slots"][0]["file_name"],
                    annotations=[],
                )
            )

    def get_annotation_data(
        self, config_values: ConfigValues
    ) -> Tuple[Dict[str, List], Dict[str, List], Dict[str, List]]:
        """
        Returns the state of the following:
        - 1: The annotations present on each item in the dataset
        - 2: The annotation classes present in the team
        - 3: The properties & property values present in the team
        """
        # 1: Get state of annotations for each item
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"ApiKey {config_values.api_key}",
        }
        item_annotations = {}
        for item in self.items:
            response = requests.get(
                f"{config_values.server}/api/v2/teams/{config_values.team_slug}/items/{item.id}/annotations",
                headers=headers,
            )
            item_annotations[item.name] = json.loads(response.text)

        # 2: Get state of annotation classes
        response = requests.get(
            f"{config_values.server}/api/teams/{config_values.team_slug}/annotation_classes",
            headers=headers,
        )
        annotation_classes = json.loads(response.text)

        # 3: Get state of properties
        response = requests.get(
            f"{config_values.server}/api/v2/teams/{config_values.team_slug}/properties?include_values=true",
            headers=headers,
        )
        properties = json.loads(response.text)

        return item_annotations, annotation_classes, properties

    def delete_items(self, config_values: ConfigValues) -> None:
        """
        Permanently deletes all items in the dataset
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"ApiKey {config_values.api_key}",
        }
        payload = {
            "filters": {
                "dataset_ids": [self.id],
                "item_ids": [str(item.id) for item in self.items],
            }
        }
        response = requests.delete(
            f"{config_values.server}/api/v2/teams/{config_values.team_slug}/items",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()


def get_read_only_registration_payload(
    item_type: str,
    dataset_slug: str,
    files_in_flat_structure: bool = False,
) -> Dict[str, str]:
    """
    Returns a payload for registering items from external storage in a read-only
    fashion. `item_type` determines what type of items will be uploaded:
    - `single_slotted`: A series of single-slotted items
    - `multi_slotted`: A single item with 3 image slots
    - `multi_channel`: A single item with 3 image channels
    - `single_slotted_video`: A single single-slotted video
    """
    path = "/" if files_in_flat_structure else None
    items = {
        "single_slotted": [
            {
                "path": path or "/",
                "type": "image",
                "storage_key": "darwin-py/images/image_1.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_1_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_1.jpg",
            },
            {
                "path": path or "/",
                "type": "image",
                "storage_key": "darwin-py/images/image_2.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_2_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_2.jpg",
            },
            {
                "path": path or "dir1",
                "type": "image",
                "storage_key": "darwin-py/images/image_3.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_3_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_3.jpg",
            },
            {
                "path": path or "dir1",
                "type": "image",
                "storage_key": "darwin-py/images/image_4.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_4_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_4.jpg",
            },
            {
                "path": path or "dir2",
                "type": "image",
                "storage_key": "darwin-py/images/image_5.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_5_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_5.jpg",
            },
            {
                "path": path or "dir2",
                "type": "image",
                "storage_key": "darwin-py/images/image_6.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_6_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_6.jpg",
            },
            {
                "path": path or "dir1/dir3",
                "type": "image",
                "storage_key": "darwin-py/images/image_7.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_7_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_7.jpg",
            },
            {
                "path": path or "dir1/dir3",
                "type": "image",
                "storage_key": "darwin-py/images/image_8.jpg",
                "storage_thumbnail_key": "darwin-py/images/image_8_thumbnail.jpg",
                "height": 1080,
                "width": 1920,
                "name": "image_8.jpg",
            },
        ],
        "multi_slotted": [
            {
                "path": path or "/",
                "layout": {
                    "slots_grid": [[["0"], ["1"], ["2"]]],
                    "version": 3,
                },
                "slots": [
                    {
                        "slot_name": "0",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_1.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_1_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_1.jpg",
                    },
                    {
                        "slot_name": "1",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_2.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_2_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_2.jpg",
                    },
                    {
                        "slot_name": "2",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_3.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_3_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_3.jpg",
                    },
                ],
                "name": "multi_slotted_item",
            },
        ],
        "multi_channel": [
            {
                "path": path or "/",
                "layout": {
                    "slots_grid": [
                        [
                            [
                                "image_1.jpg",
                                "image_2.jpg",
                                "image_3.jpg",
                            ]
                        ]
                    ],
                    "version": 3,
                },
                "slots": [
                    {
                        "slot_name": "image_1.jpg",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_1.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_1_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_1.jpg",
                    },
                    {
                        "slot_name": "image_2.jpg",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_2.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_2_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_2.jpg",
                    },
                    {
                        "slot_name": "image_3.jpg",
                        "type": "image",
                        "storage_key": "darwin-py/images/image_3.jpg",
                        "storage_thumbnail_key": "darwin-py/images/image_3_thumbnail.jpg",
                        "height": 1080,
                        "width": 1920,
                        "file_name": "image_3.jpg",
                    },
                ],
                "name": "multi_channel_item",
            },
        ],
        "single_slotted_video": [
            {
                "path": path or "/",
                "type": "video",
                "storage_key": "darwin-py/videos/mini_uct.mp4",
                "storage_thumbnail_key": "darwin-py/videos/video_thumbnail.jpg",
                "name": "mini_uct.mp4",
                "sections": [
                    {
                        "section_index": 1,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_1_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_1_lq.jpg",
                    },
                    {
                        "section_index": 2,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_2_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_2_lq.jpg",
                    },
                    {
                        "section_index": 3,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_3_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_3_lq.jpg",
                    },
                    {
                        "section_index": 4,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_4_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_4_lq.jpg",
                    },
                    {
                        "section_index": 5,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_5_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_5_lq.jpg",
                    },
                    {
                        "section_index": 6,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_6_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_6_lq.jpg",
                    },
                    {
                        "section_index": 7,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_7_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_7_lq.jpg",
                    },
                    {
                        "section_index": 8,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_8_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_8_lq.jpg",
                    },
                    {
                        "section_index": 9,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_9_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_9_lq.jpg",
                    },
                    {
                        "section_index": 10,
                        "height": 1080,
                        "width": 1920,
                        "storage_hq_key": "darwin-py/videos/hq_frames/image_10_hq.jpg",
                        "storage_lq_key": "darwin-py/videos/hq_frames/image_10_lq.jpg",
                    },
                ],
            }
        ],
        "multi_slotted_dicom": [
            {
                "path": path or "/",
                "layout": {
                    "slots": ["0", "1"],
                    "type": "horizontal",
                    "version": 1,
                },
                "slots": [
                    {
                        "type": "dicom",
                        "file_name": "file_1.dcm",
                        "storage_key": "darwin-py/dicoms/file_1.dcm",
                        "storage_thumbnail_key": "darwin-py/images/image_3_thumbnail.jpg",
                        "sections": [
                            {
                                "section_index": 1,
                                "height": 1080,
                                "width": 1920,
                                "storage_hq_key": "darwin-py/videos/hq_frames/image_1_hq.jpg",
                                "storage_lq_key": "darwin-py/videos/hq_frames/image_1_lq.jpg",
                            },
                        ],
                        "slot_name": "0",
                    },
                    {
                        "type": "dicom",
                        "file_name": "file_2.dcm",
                        "storage_key": "darwin-py/dicoms/file_2.dcm",
                        "storage_thumbnail_key": "darwin-py/images/image_3_thumbnail.jpg",
                        "sections": [
                            {
                                "section_index": 1,
                                "height": 1080,
                                "width": 1920,
                                "storage_hq_key": "darwin-py/videos/hq_frames/image_1_hq.jpg",
                                "storage_lq_key": "darwin-py/videos/hq_frames/image_1_lq.jpg",
                            },
                        ],
                        "slot_name": "1",
                    },
                ],
                "name": "multi_slotted_dicom_item",
            },
        ],
    }
    return {
        "items": items[item_type],  # type: ignore
        "dataset_slug": dataset_slug,
        "storage_slug": "darwin-e2e-data",
    }


@dataclass
class E2ETestRunInfo:
    prefix: str
    datasets: List[E2EDataset]
