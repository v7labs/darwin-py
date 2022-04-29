import datetime
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from darwin.dataset.identifier import DatasetIdentifier


class Release:
    """
    Represents a release/export. Releases created this way can only contain items with 'completed'
    status.

    Parameters
    ----------
    dataset_slug : str
        The slug of the dataset.
    team_slug : str
        the slug of the team.
    version : str
        The version of the ``Release``.
    name : str
        The name of the ``Release``.
    url : Optional[str]
        The full url used to download the ``Release``.
    export_date : datetime.datetime
        The ``datetime`` of when this release was created.
    image_count : Optional[int]
        Number of images in this ``Release``.
    class_count : Optional[int]
        Number of distinct classes in this ``Release``.
    available : bool
        If this ``Release`` is downloadable or not.
    latest : bool
        If this ``Release`` is the latest one or not.
    format : str
        Format for the file of this ``Release`` should it be downloaded.

    Attributes
    ----------
    dataset_slug : str
        The slug of the dataset.
    team_slug : str
        the slug of the team.
    version : str
        The version of the ``Release``.
    name : str
        The name of the ``Release``.
    url : Optional[str]
        The full url used to download the ``Release``.
    export_date : datetime.datetime
        The ``datetime`` of when this release was created.
    image_count : Optional[int]
        Number of images in this ``Release``.
    class_count : Optional[int]
        Number of distinct classes in this ``Release``.
    available : bool
        If this ``Release`` is downloadable or not.
    latest : bool
        If this ``Release`` is the latest one or not.
    format : str
        Format for the file of this ``Release`` should it be downloaded.
    """

    def __init__(
        self,
        dataset_slug: str,
        team_slug: str,
        version: str,
        name: str,
        url: Optional[str],
        export_date: datetime.datetime,
        image_count: Optional[int],
        class_count: Optional[int],
        available: bool,
        latest: bool,
        format: str,
    ):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version
        self.name = name
        self.url = url
        self.export_date = export_date
        self.image_count = image_count
        self.class_count = class_count
        self.available = available
        self.latest = latest
        self.format = format

    @classmethod
    def parse_json(cls, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> "Release":
        """
        Given a json, parses it into a ``Release`` object instance.

        Parameters
        ----------
        dataset_slug : str
            The slug of the dataset this ``Release`` belongs to.
        team_slug : str
            The slug of the team this ``Release``'s dataset belongs to.
        payload : Dict[str, Any]
            A Dictionary with the ``Release`` information. It must have a minimal format similar to:

            .. code-block:: javascript

                {
                    "version": "a_version",
                    "name": "a_name"
                }

            If no ``format`` key is found in ``payload``, the default will be ``json``.

            Optional ``payload`` has no ``download_url`` key, then ``url``, ``available``,
            ``image_count``, ``class_count`` and ``latest`` will default to either ``None`` or
            ``False`` depending on the type.

            A more complete format for this parameter would be similar to:

            .. code-block:: javascript

                {
                    "version": "a_version",
                    "name": "a_name",
                    "metadata": {
                        "num_images": 1,
                        "annotation_classes": []
                    },
                    "download_url": "http://www.some_url_here.com",
                    "latest": false,
                    "format": "a_format"
                }

        Returns
        -------
        Release
            A ``Release`` created from the given payload.
        """
        try:
            export_date: datetime.datetime = datetime.datetime.strptime(payload["inserted_at"], "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            # For python version older than 3.7
            export_date = datetime.datetime.strptime(payload["inserted_at"], "%Y-%m-%dT%H:%M:%SZ")

        if payload["download_url"] is None:
            return cls(
                dataset_slug=dataset_slug,
                team_slug=team_slug,
                version=payload["version"],
                name=payload["name"],
                export_date=export_date,
                url=None,
                available=False,
                image_count=None,
                class_count=None,
                latest=False,
                format=payload.get("format", "json"),
            )

        return cls(
            dataset_slug=dataset_slug,
            team_slug=team_slug,
            version=payload["version"],
            name=payload["name"],
            image_count=payload["metadata"]["num_images"],
            class_count=len(payload["metadata"]["annotation_classes"]),
            export_date=export_date,
            url=payload["download_url"],
            available=True,
            latest=payload["latest"],
            format=payload.get("format", "json"),
        )

    def download_zip(self, path: Path) -> Path:
        """
        Downloads the release content into a zip file located by the given path.

        Parameters
        ----------
        path : Path
            The path where the zip file will be located.

        Returns
        --------
        Path
            Same ``Path`` as provided in the parameters.

        Raises
        ------
        ValueError
            If this ``Release`` object does not have a specified url.
        """
        if not self.url:
            raise ValueError("Release must have a valid url to download the zip.")

        with requests.get(self.url, stream=True) as response:
            with open(path, "wb") as download_file:
                shutil.copyfileobj(response.raw, download_file)

        return path

    @property
    def identifier(self) -> DatasetIdentifier:
        """DatasetIdentifier : The ``DatasetIdentifier`` for this ``Release``."""
        return DatasetIdentifier(team_slug=self.team_slug, dataset_slug=self.dataset_slug, version=self.name)
