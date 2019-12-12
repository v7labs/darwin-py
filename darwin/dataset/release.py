import datetime
import shutil

import requests


class Release:
    def __init__(
        self, dataset_slug, team_slug, version, url, export_date, image_count, class_count
    ):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version
        self.url = url
        self.export_date = export_date
        self.image_count = image_count
        self.class_count = class_count

    @classmethod
    def parse_json(cls, dataset_slug, team_slug, payload):
        export_date = datetime.datetime.strptime(
            payload["inserted_at"], "%Y-%m-%dT%H:%M:%S"
        )  # TODO: We should add %Z for timezones
        return cls(
            dataset_slug=dataset_slug,
            team_slug=team_slug,
            version=payload["version"],
            image_count=payload["metadata"]["num_images"],
            class_count=payload["metadata"]["num_classes"],
            export_date=export_date,
            url=payload["download_url"],
        )

    def download_zip(self, path):
        with requests.get(self.url, stream=True) as r:
            with open(str(path), "wb") as f:
                shutil.copyfileobj(r.raw, f)
        return path

    @property
    def versioned_name(self):
        return f"{self.team_slug}/{self.dataset_slug}:{self.version}"
