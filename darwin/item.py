from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import deprecation
from pydantic import BaseModel

from darwin.path_utils import construct_full_path
from darwin.version import __version__


@dataclass(frozen=True, eq=True)
class DatasetItem(BaseModel):
    """
    DatasetItem represents files that can be images or videos which belong to a dataset.
    """

    #: The id of this ``DatasetItem``.
    id: int

    #: The filename of this ``DatasetItem``.
    filename: str

    #: The status of this ``DatasetItem``. It can be ``"archived"``, ``"error"``, ``"uploading"``,
    #: ``"processing"``, ``"new"``, ``"annotate"``, ``"review"`` or ``"complete"``.
    status: str

    #: Whether or not this item was soft deleted.
    archived: bool

    #: The size of this ``DatasetItem``\'s file in bytes.
    filesize: int

    #: The id of the ``Dataset`` this ``DatasetItem`` belongs to.
    dataset_id: int

    #: The slugified name of the ``Dataset`` this ``DatasetItem`` belongs to.
    dataset_slug: str

    #: The sequential value of this ``DatasetItem`` in relation to the ``Dataset`` it belongs to.
    #: This allows us to know which items were added first and is used mostly for sorting purposes.
    seq: int

    #: The id of this ``DatasetItem``'s workflow. A ``None`` value means this ``DatasetItem`` is
    #: new and was never worked on, or was reset to the new state.
    current_workflow_id: Optional[int]

    #: The darwin path to this ``DatasetItem``.
    path: str

    #: The names of each slot in the item, most items have a single slot corresponding to the file itself.
    #: only used for v2 dataset items
    slots: List[Any]

    #: Metadata of this ``DatasetItem``'s workflow. A ``None`` value means this ``DatasetItem`` is
    #: new and was never worked on, or was reset to the new state.
    current_workflow: Optional[Dict[str, Any]]

    @property
    def full_path(self) -> str:
        """
        The full POSIX relative path of this ``DatasetItem``.
        """
        return construct_full_path(self.path, self.filename)

    @classmethod
    def parse(cls, raw: Dict[str, Any]) -> "DatasetItem":
        """
        Parses the given dictionary into a ``DatasetItem``.

        Parameters
        ----------
        raw : Dict[str, Any]
            The dictionary to parse.

        Returns
        -------
        DatasetItem
            A dataset item with the parsed information.

        Raises
        ------
        ValidationError
            If any of the keys from the given dictionary do not have the correct format or are
            missing.
        """
        if "slots" in raw:
            data = {
                "id": raw["id"],
                "filename": raw["name"],
                "path": raw["path"],
                "status": raw["status"],
                "archived": raw["archived"],
                "filesize": sum(file.get("size_bytes", 0) for file in raw["slots"]),
                "dataset_id": raw["dataset_id"],
                "dataset_slug": "n/a",
                "seq": None,
                "current_workflow_id": None,
                "current_workflow": None,
                "slots": raw["slots"],
                "current_workflow": None,
            }
        else:
            data = {
                "id": raw["id"],
                "filename": raw["filename"],
                "status": raw["status"],
                "archived": raw["archived"],
                "filesize": raw["file_size"],
                "dataset_id": raw["dataset_id"],
                "dataset_slug": "n/a",
                "seq": raw["seq"],
                "current_workflow_id": raw.get("current_workflow_id"),
                "current_workflow": raw.get("current_workflow"),
                "path": raw["path"],
                "slots": [],
            }
        return DatasetItem(**data)


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Use the ``DatasetItem.parse`` instead.",
)
def parse_dataset_item(raw: Dict[str, Any]) -> DatasetItem:
    """
    Parses the given dictionary into a ``DatasetItem``. Performs no validations.

    Parameters
    ----------
    raw : Dict[str, Any]
        The dictionary to parse.

    Returns
    -------
    DatasetItem
        A dataset item with the parsed information.
    """
    return DatasetItem(
        raw["id"],
        raw["filename"],
        raw["status"],
        raw["archived"],
        raw["file_size"],
        raw["dataset_id"],
        "n/a",
        raw["seq"],
        raw.get("current_workflow_id"),
        raw["path"],
        [],
        raw.get("current_workflow"),
    )
