from dataclasses import dataclass
from typing import Any, Dict, Optional

import deprecation

from darwin.path_utils import construct_full_path
from darwin.utils import current_version


@dataclass(frozen=True, eq=True)
class DatasetItem:
    """
    DatasetItem represents files that can be images or videos which belong to a dataset.

    Attributes
    ----------
    id : int
        The id of this ``DatasetItem``.
    filename : str
        The filename of this ``DatasetItem``.
    status : str
        The status of this ``DatasetItem``. It can be:
        - "archived",
        - "error",
        - "uploading",
        - "processing",
        - "new",
        - "annotate",
        - "review",
        - "complete"
    archived : bool
        Whether or not this item was soft deleted.
    filesize : int
        The size of this ``DatasetItem``'s file in bytes.
    dataset_id : int
        The id of the ``Dataset`` this ``DatasetItem`` belongs to.
    dataset_slug : str
        The slugified name of the ``Dataset`` this ``DatasetItem`` belongs to.
    seq : int
        The sequential value of this ``DatasetItem`` in relation to the ``Dataset`` it belongs to.
        This allows us to know which items were added first and is used mostly for sorting purposes.
    current_workflow_id : Optional[int], default : None
        The id of this ``DatasetItem``'s workflow. A ``None`` value means this ``DatasetItem`` is
        new and was never worked on, or was reseted to the new state.
    path : str
        The darwin path to this ``DatasetItem``.
    """

    id: int
    filename: str
    status: str
    archived: bool
    filesize: int
    dataset_id: int
    dataset_slug: str
    seq: int
    current_workflow_id: Optional[int]
    path: str

    @property
    def full_path(self) -> str:
        """
        The full POSIX relative path of this ``DatasetItem``.
        """
        return construct_full_path(self.path, self.filename)

    @classmethod
    def parse(cls, raw: Dict[str, Any]) -> "DatasetItem":
        """
        Parses the given dictionary into a ``DatasetItem``. Raises if such is not possible.

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
        ValueError
            If any of the keys from the given dictionary do not have the correct format.
        """
        id: int = raw["id"]
        if not isinstance(id, int):
            raise ValueError("Key 'id' must have an integer for a value.")

        filename: str = raw["filename"]
        if not isinstance(filename, str):
            raise ValueError("Key 'filename' must have a string for a value.")

        status: str = raw["status"]
        if not isinstance(status, str):
            raise ValueError("Key 'status' must have a string for a value.")

        archived: bool = raw["archived"]
        if not isinstance(archived, bool):
            raise ValueError("Key 'archived' must have a boolean for a value.")

        file_size: int = raw["file_size"]
        if not isinstance(file_size, int):
            raise ValueError("Key 'file_size' must have an integer for a value.")

        dataset_id: int = raw["dataset_id"]
        if not isinstance(dataset_id, int):
            raise ValueError("Key 'dataset_id' must have an integer for a value.")

        sequence: int = raw["seq"]
        if not isinstance(sequence, int):
            raise ValueError("Key 'seq' must have an integer for a value.")

        workflow_id: Optional[int] = raw.get("current_workflow_id")
        if not isinstance(workflow_id, int) and workflow_id is not None:
            raise ValueError("Key 'workflow_id' must have an integer for a value or be nil.")

        path: str = raw["path"]
        if not isinstance(path, str):
            raise ValueError("Key 'path' must have a string for a value.")

        return DatasetItem(
            id,
            filename,
            status,
            archived,
            file_size,
            dataset_id,
            "n/a",
            sequence,
            workflow_id,
            path,
        )


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=current_version(),
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
    )
