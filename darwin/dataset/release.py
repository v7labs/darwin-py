import datetime
import shutil
from pathlib import Path
from typing import Optional

import requests
from darwin.dataset.identifier import DatasetIdentifier


class Release:
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
    def parse_json(cls, dataset_slug, team_slug, payload) -> "Release":
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
            Same Path as provided in the parameters.
        
        Raises
        ------
        ValueError
            If this Release object does not have a specified url.
        """
        if not self.url:
            raise ValueError("Relase must have a valid url to download the zip.")

        with requests.get(self.url, stream=True) as response:
            with open(path, "wb") as download_file:
                shutil.copyfileobj(response.raw, download_file)

        return path

    @property
    def identifier(self) -> DatasetIdentifier:
        return DatasetIdentifier(team_slug=self.team_slug, dataset_slug=self.dataset_slug, version=self.name)
