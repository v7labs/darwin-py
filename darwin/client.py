import json
import logging
import os
import time
import zlib
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union, cast
from urllib import parse

import requests
from requests import Response

from darwin.backend_v2 import BackendV2
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import DarwinVersionNumber, Feature, ItemId, Team
from darwin.exceptions import (
    InsufficientStorage,
    InvalidLogin,
    MissingConfig,
    NameTaken,
    NotFound,
    RequestEntitySizeExceeded,
    Unauthorized,
    ValidationError,
)
from darwin.item import DatasetItem
from darwin.utils import (
    get_response_content,
    has_json_content_type,
    is_project_dir,
    urljoin,
)


class Client:
    def __init__(self, config: Config, default_team: Optional[str] = None, log: Optional[Logger] = None):
        self.config: Config = config
        self.url: str = config.get("global/api_endpoint")
        self.base_url: str = config.get("global/base_url")
        self.default_team: str = default_team or config.get("global/default_team")
        self.features: Dict[str, List[Feature]] = {}
        self._newer_version: Optional[DarwinVersionNumber] = None
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=100)
        self.session.mount("https://", adapter)

        if log is None:
            self.log: Logger = logging.getLogger("darwin")
        else:
            self.log = log

    def list_local_datasets(self, team_slug: Optional[str] = None) -> Iterator[Path]:
        """
        Returns a list of all local folders which are detected as dataset.

        Parameters
        ----------
        team_slug: Optional[str]
            The team slug of the dataset. Defaults to None.


        Returns
        -------
        Iterator[Path]
            Iterator of all local datasets
        """

        team_configs: List[Team] = []
        if team_slug:
            team_data: Optional[Team] = self.config.get_team(team_slug)
            if team_data:
                team_configs.append(team_data)
        else:
            team_configs = self.config.get_all_teams()

        for team_config in team_configs:
            projects_team: Path = Path(team_config.datasets_dir) / team_config.slug
            for project_path in projects_team.glob("*"):
                if project_path.is_dir() and is_project_dir(project_path):
                    yield Path(project_path)

    def list_remote_datasets(self, team_slug: Optional[str] = None) -> Iterator[RemoteDataset]:
        """
        Returns a list of all available datasets with the team currently authenticated against.

        Parameters
        ----------
        team_slug: Optional[str]
            The team slug of the dataset. Defaults to None.

        Returns
        -------
        Iterator[RemoteDataset]
            List of all remote datasets
        """
        response: List[Dict[str, Any]] = cast(List[Dict[str, Any]], self._get("/datasets/", team_slug=team_slug))

        for dataset in response:
            if dataset.get("version", 1) == 2:
                yield RemoteDatasetV2(
                    name=dataset["name"],
                    slug=dataset["slug"],
                    team=team_slug or self.default_team,
                    dataset_id=dataset["id"],
                    item_count=dataset.get("num_items", dataset.get("num_images", 0) + dataset.get("num_videos", 0)),
                    progress=dataset["progress"],
                    client=self,
                )
            else:
                yield RemoteDatasetV1(
                    name=dataset["name"],
                    slug=dataset["slug"],
                    team=team_slug or self.default_team,
                    dataset_id=dataset["id"],
                    item_count=dataset.get("num_images", 0) + dataset.get("num_videos", 0),
                    progress=dataset["progress"],
                    client=self,
                )

    def get_remote_dataset(self, dataset_identifier: Union[str, DatasetIdentifier]) -> RemoteDataset:
        """
        Get a remote dataset based on its identifier.

        Parameters
        ----------
        dataset_identifier : Union[str, DatasetIdentifier]
            Identifier of the dataset. Can be the string version or a DatasetIdentifier object.

        Returns
        -------
        RemoteDataset
            Initialized dataset.

        Raises
        -------
        NotFound
            If no dataset with the given identifier was found.
        """
        parsed_dataset_identifier: DatasetIdentifier = DatasetIdentifier.parse(dataset_identifier)

        if not parsed_dataset_identifier.team_slug:
            parsed_dataset_identifier.team_slug = self.default_team

        try:
            matching_datasets: List[RemoteDataset] = [
                dataset
                for dataset in self.list_remote_datasets(team_slug=parsed_dataset_identifier.team_slug)
                if dataset.slug == parsed_dataset_identifier.dataset_slug
            ]
        except Unauthorized:
            # There is a chance that we tried to access an open dataset
            dataset: Dict[str, Any] = cast(
                Dict[str, Any],
                self._get(f"{parsed_dataset_identifier.team_slug}/{parsed_dataset_identifier.dataset_slug}"),
            )

            # If there isn't a record of this team, create one.
            if not self.config.get_team(parsed_dataset_identifier.team_slug, raise_on_invalid_team=False):
                datasets_dir: Path = Path.home() / ".darwin" / "datasets"
                self.config.set_team(
                    team=parsed_dataset_identifier.team_slug, api_key="", datasets_dir=str(datasets_dir)
                )

            if dataset.get("version", 1) == 2:
                return RemoteDatasetV2(
                    name=dataset["name"],
                    slug=dataset["slug"],
                    team=parsed_dataset_identifier.team_slug,
                    dataset_id=dataset["id"],
                    item_count=dataset.get("num_items", dataset.get("num_images", 0) + dataset.get("num_videos", 0)),
                    progress=0,
                    client=self,
                )
            else:
                return RemoteDatasetV1(
                    name=dataset["name"],
                    slug=dataset["slug"],
                    team=parsed_dataset_identifier.team_slug,
                    dataset_id=dataset["id"],
                    item_count=dataset.get("num_items", dataset.get("num_images", 0) + dataset.get("num_videos", 0)),
                    progress=0,
                    client=self,
                )
        if not matching_datasets:
            raise NotFound(str(parsed_dataset_identifier))
        return matching_datasets[0]

    def create_dataset(self, name: str, team_slug: Optional[str] = None) -> RemoteDataset:
        """
        Create a remote dataset.

        Parameters
        ----------
        name : str
            Name of the dataset to create.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        -------
        RemoteDataset
            The created dataset.
        """
        dataset: Dict[str, Any] = cast(Dict[str, Any], self._post("/datasets", {"name": name}, team_slug=team_slug))
        if dataset.get("version", 1) == 2:
            return RemoteDatasetV2(
                name=dataset["name"],
                team=team_slug or self.default_team,
                slug=dataset["slug"],
                dataset_id=dataset["id"],
                item_count=dataset.get("num_items", dataset.get("num_images", 0) + dataset.get("num_videos", 0)),
                progress=0,
                client=self,
            )
        else:
            return RemoteDatasetV1(
                name=dataset["name"],
                team=team_slug or self.default_team,
                slug=dataset["slug"],
                dataset_id=dataset["id"],
                item_count=dataset.get("num_items", dataset.get("num_images", 0) + dataset.get("num_videos", 0)),
                progress=0,
                client=self,
            )
        end

    def archive_remote_dataset(self, dataset_id: int, team_slug: str) -> None:
        """
        Archive (soft delete) a remote dataset.

        Parameters
        ----------
        dataset_id: int
            Id of the dataset to archive.
        team_slug: str
            Team slug of the dataset.
        """
        self._put(f"datasets/{dataset_id}/archive", payload={}, team_slug=team_slug)

    def fetch_remote_files(
        self, dataset_id: int, cursor: Dict[str, Any], payload: Dict[str, Any], team_slug: str
    ) -> Dict[str, Any]:
        """
        Download the remote files from the given dataset.

        Parameters
        ----------
        dataset_id: int
            Id of the dataset the file belong to.
        cursor: Dict[str, Any]
            Number of items per page and page number. Defaults to {"page[size]": 500, "page[from]": 0}.
        payload: Dict[str, Any]
            Filter and sort parameters.
        team_slug: str
            The team slug of the dataset.

        Returns
        -------
         Dict[str, Any]
            A response dictionary with the file information.
        """
        response: Dict[str, Any] = cast(
            Dict[str, Any], self._post(f"/datasets/{dataset_id}/items?{parse.urlencode(cursor)}", payload, team_slug)
        )
        return response

    def fetch_remote_classes(self, team_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches all remote classes on the remote dataset.

        Parameters
        ----------
        team_slug: Optional[str]
            The team slug of the dataset. Defaults to None.

        Returns
        -------
        Dict[str, Any]
            None if no information about the team is found, a List of Annotation classes otherwise.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        the_team_slug: str = the_team.slug
        response: Dict[str, Any] = cast(
            Dict[str, Any], self._get(f"/teams/{the_team_slug}/annotation_classes?include_tags=true")
        )

        return response["annotation_classes"]

    def update_annotation_class(self, class_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the AnnotationClass with the given id.

        Parameters
        ----------
        class_id: int
            The id of the AnnotationClass to update.
        payload: Dict[str, Any]
            A dictionary with the changes to perform.

        Returns
        -------
        Dict[str, Any]
            A dictionary with the result of the operation.
        """
        response: Dict[str, Any] = cast(Dict[str, Any], self._put(f"/annotation_classes/{class_id}", payload))
        return response

    def create_annotation_class(self, dataset_id: int, type_ids: List[int], name: str) -> Dict[str, Any]:
        """
        Creates an AnnotationClass.

        Parameters
        ----------
        dataset_id: int
            The id of the dataset this AnnotationClass will belong to originaly.
        type_ids: List[int]
            A list of type ids for the annotations this class will hold.
        name: str
            The name of the annotation class.

        Returns
        -------
        Dict[str, Any]
            A dictionary with the result of the operation.
        """
        response: Dict[str, Any] = cast(
            Dict[str, Any],
            self._post(
                "/annotation_classes",
                payload={
                    "dataset_id": dataset_id,
                    "name": name,
                    "metadata": {"_color": "auto"},
                    "annotation_type_ids": type_ids,
                    "datasets": [{"id": dataset_id}],
                },
            ),
        )
        return response

    def import_annotation(self, item_id: ItemId, payload: Dict[str, Any]) -> None:
        """
        Imports the annotation for the item with the given id.

        Parameters
        ----------
        item_id: ItemId
            Identifier of the Image or Video that we are import the annotation to.
        payload: Dict[str, Any]
            A dictionary with the annotation to import. The default format is:
            `{"annotations": serialized_annotations, "overwrite": "false"}`
        """

        self._post_raw(f"/dataset_items/{item_id}/import", payload=payload)

    def fetch_remote_attributes(self, dataset_id: int) -> List[Dict[str, Any]]:
        """
        Fetches all attributes remotely.

        Parameters
        ----------
        dataset_id: int
            The id of the dataset with the attributes we want to fetch.


        Returns
        -------
        List[Dict[str, Any]]
            A List with the attributes, where each attribute is a dictionary.
        """
        response: List[Dict[str, Any]] = cast(List[Dict[str, Any]], self._get(f"/datasets/{dataset_id}/attributes"))
        return response

    def load_feature_flags(self, team_slug: Optional[str] = None) -> None:
        """
        Loads in memory the set of current features enabled for a team.

        Parameters
        ----------
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.
        """

        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            return None

        the_team_slug: str = the_team.slug
        self.features[the_team_slug] = self.get_team_features(the_team_slug)

    def get_team_features(self, team_slug: str) -> List[Feature]:
        """
        Gets all the features for the given team together with their statuses.

        Parameters
        ----------
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        -------
        List[Feature]
            List of Features for the given team.
        """
        response: List[Dict[str, Any]] = cast(List[Dict[str, Any]], self._get(f"/teams/{team_slug}/features"))

        features: List[Feature] = []
        for feature in response:
            features.append(Feature(name=str(feature["name"]), enabled=bool(feature["enabled"])))

        return features

    def feature_enabled(self, feature_name: str, team_slug: Optional[str] = None) -> bool:
        """
        Returns whether or not a given feature is enabled for a team.

        Parameters
        ----------
        feature_name: str
            The name of the feature.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        -------
        bool
            False if the given feature is not enabled OR the team was not found. True otherwise.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            return False

        the_team_slug: str = the_team.slug

        if the_team_slug not in self.features:
            self.load_feature_flags(the_team_slug)

        team_features: List[Feature] = self.features[the_team_slug]
        for feature in team_features:
            if feature.name == feature_name:
                return feature.enabled

        return False

    def get_datasets_dir(self, team_slug: Optional[str] = None) -> str:
        """
        Gets the dataset directory of the specified team or the default one

        Parameters
        ----------
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        -------
        str
            Path of the datasets for the selected team or the default one, or None if the Team was
            not found.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        return the_team.datasets_dir

    def set_datasets_dir(self, datasets_dir: Path, team_slug: Optional[str] = None) -> None:
        """
        Sets the dataset directory of the specified team or the default one.

        Parameters
        ----------
        datasets_dir: Path
            Path to set as dataset directory of the team.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.
        """
        self.config.put(f"teams/{team_slug or self.default_team}/datasets_dir", datasets_dir)

    def confirm_upload(self, dataset_item_id: int, team_slug: Optional[str] = None) -> None:
        """
        Confirms that the item was uploaded.

        Parameters
        ----------
        dataset_item_id: int
            The id of the DatasetItem that was uploaded.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            return None

        the_team_slug: str = the_team.slug

        self._put_raw(endpoint=f"/dataset_items/{dataset_item_id}/confirm_upload", payload={}, team_slug=the_team_slug)

    def sign_upload(self, dataset_item_id: int, team_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Signs the upload of the given DatasetItem.

        Parameters
        ----------
        dataset_item_id: int
            The id of the DatasetItem that was uploaded.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        ------
        Dict[str, Any]
            A dictionary with the signed response, or None if the Team was not found.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        the_team_slug: str = the_team.slug

        response: Dict[str, Any] = cast(
            Dict[str, Any], self._get(f"/dataset_items/{dataset_item_id}/sign_upload", team_slug=the_team_slug)
        )
        return response

    def upload_data(
        self, dataset_slug: str, payload: Dict[str, Any], team_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads the given data to the given dataset.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        payload: Dict[str, Any]
            The data we want to upload. Usually a Dictionary with an `items` key containing a list
            of items to upload.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        ------
        Dict[str, Any]
            A dictionary with the result of the operation, or None if the Team was not found.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        the_team_slug: str = the_team.slug

        response: Dict[str, Any] = cast(
            Dict[str, Any],
            self._put(
                endpoint=f"/teams/{the_team_slug}/datasets/{dataset_slug}/data",
                payload=payload,
                team_slug=the_team_slug,
            ),
        )
        return response

    def annotation_types(self) -> List[Dict[str, Any]]:
        """
        Returns a list of annotation types.

        Returns
        ------
        List[Dict[str, Any]]
            A list with the annotation types as dictionaries.
        """
        response: List[Dict[str, Any]] = cast(List[Dict[str, Any]], self._get("/annotation_types"))
        return response

    def get_exports(self, dataset_id: int, team_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all the exports from the given dataset.

        Parameters
        ----------
        dataset_id: int
            The id of the dataset.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        ------
        List[Dict[str, Any]]
            A list with all the exports (as dictionaries) or None if the Team was not found.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        the_team_slug: str = the_team.slug

        response: List[Dict[str, Any]] = cast(
            List[Dict[str, Any]], self._get(f"/datasets/{dataset_id}/exports", team_slug=the_team_slug)
        )
        return response

    def create_export(self, dataset_id: int, payload: Dict[str, Any], team_slug: str) -> None:
        """
        Create an export for the given dataset.

        Parameters
        ----------
        dataset_id: int
            The id of the dataset.
        payload: Dict[str, Any]
            The export infomation as a Dictionary.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.
        """
        self._post(f"/datasets/{dataset_id}/exports", payload=payload, team_slug=team_slug)

    def get_report(self, dataset_id: int, granularity: str, team_slug: Optional[str] = None) -> Response:
        """
        Gets the report for the given dataset.

        Parameters
        ----------
        dataset_id: int
            The id of the dataset.
        granularity: str
            Granularity of the report, can be 'day', 'week' or 'month'.
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        ------
        Response
            The raw response of the report (CSV format) or None if the Team was not found.

        Raises
        ------
        ValueError
            If no team was found.
        """
        the_team: Optional[Team] = self.config.get_team(team_slug or self.default_team)

        if not the_team:
            raise ValueError("No team was found.")

        the_team_slug: str = the_team.slug

        return self._get_raw(
            f"/reports/{the_team_slug}/annotation?group_by=dataset,user&dataset_ids={dataset_id}&granularity={granularity}&format=csv&include=dataset.name,user.first_name,user.last_name,user.email",
            the_team_slug,
        )

    def delete_item(self, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> None:
        """
        Gets the report for the given dataset.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be deleted.
        """
        self._delete(f"teams/{team_slug}/datasets/{dataset_slug}/items", payload, team_slug)

    def archive_item(self, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> None:
        """
        Archives the item from the given dataset.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be archived.
        """
        self._put_raw(f"teams/{team_slug}/datasets/{dataset_slug}/items/archive", payload, team_slug)

    def restore_archived_item(self, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> None:
        """
        Restores the archived item from the given dataset.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be restored.
        """
        self._put_raw(f"teams/{team_slug}/datasets/{dataset_slug}/items/restore", payload, team_slug)

    def move_item_to_new(self, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> None:
        """
        Moves the given item's status to new.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to have the 'new' status.
        """
        self._put_raw(f"teams/{team_slug}/datasets/{dataset_slug}/items/move_to_new", payload, team_slug)

    def reset_item(self, dataset_slug: str, team_slug: str, payload: Dict[str, Any]) -> None:
        """
        Resets the given item.

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be reset.
        """
        self._put_raw(f"teams/{team_slug}/datasets/{dataset_slug}/items/reset", payload, team_slug)

    def move_to_stage(self, dataset_slug: str, team_slug: str, filters: Dict[str, Any], stage_id: int) -> None:
        """
        Moves the given items to the specified stage

        Parameters
        ----------
        dataset_slug: str
            The slug of the dataset.
        team_slug: str
            The slug of the team.
        filters: Dict[str, Any]
            A filter Dictionary that defines the items to have the new, selected stage.
        stage_id: int
            ID of the stage to set.
        """
        payload: Dict[str, Any] = {
            "filter": filters,
            "workflow_stage_template_id": stage_id,
        }
        self._put_raw(f"teams/{team_slug}/datasets/{dataset_slug}/set_stage", payload, team_slug)

    def post_workflow_comment(
        self, workflow_id: int, text: str, x: float = 1, y: float = 1, w: float = 1, h: float = 1
    ) -> int:
        """
        Creates a comment box with the given text for the given workflow.

        Parameters
        ----------
        workflow_id: int
            The id of the workflow that will receive the comment.
        text: str
            The comment itself.
        x: float, default: 1
            The top left X coordinate value of the comment box.
        y: float, default: 1
            The top left Y coordinate value of the comment box.
        w: float, default: 1
            The width of the comment box.
        h: float, default: 1
            The height of the comment box.

        Returns
        -------
        int
            The id of the created comment.
        """
        response: Dict[str, Any] = cast(
            Dict[str, Any],
            self._post(
                f"workflows/{workflow_id}/workflow_comment_threads",
                {"bounding_box": {"x": x, "y": y, "w": w, "h": h}, "workflow_comments": [{"body": text}]},
            ),
        )

        comment_id: Optional[int] = response.get("id")
        if comment_id is None:
            raise ValueError(f"Unable to retrieve comment id for workflow: {workflow_id}.")

        return comment_id

    def instantiate_item(self, item_id: int, include_metadata: bool = False) -> Union[int, Tuple[int, DatasetItem]]:
        """
        Instantiates the given item with a workflow.

        Parameters
        ----------
        item_id: int
            The id of the item to be instantiated.

        include_metadata: bool
            If set to True, this method returns a tuple instead, with 2nd element being DatasetItem.

        Returns
        -------
        int
            The id of the workflow for the given item.

        Raises
        ------
        ValueError
            If due to an error, no workflow was instantiated for this item an therefore no workflow id can be returned.
        """
        response: Dict[str, Any] = cast(Dict[str, Any], self._post(f"dataset_items/{item_id}/workflow"))
        id: Optional[int] = response.get("current_workflow_id")

        if id is None:
            raise ValueError(f"No Workflow Id found for item_id: {item_id}")

        if include_metadata:
            return (id, DatasetItem.parse(response))
        else:
            return id

    def fetch_binary(self, url: str) -> Response:
        """
        Fetches binary data from the given url via a stream.

        Parameters
        ----------
        url: str
            The full url to download the binary data.

        Returns
        -------
        Response
            ``request``'s Response object.
        """
        response: Response = cast(Response, self._get_raw_from_full_url(url, stream=True))
        return response

    @classmethod
    def local(cls, team_slug: Optional[str] = None) -> "Client":
        """
        Factory method to use the default configuration file to init the client

        Parameters
        ----------
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.

        Returns
        -------
        Client
            The initialized client.
        """
        config_path: Path = Path.home() / ".darwin" / "config.yaml"
        return Client.from_config(config_path, team_slug=team_slug)

    @classmethod
    def from_config(cls, config_path: Path, team_slug: Optional[str] = None) -> "Client":
        """
        Factory method to create a client from the configuration file passed as parameter

        Parameters
        ----------
        config_path : str
            Path to a configuration file to use to create the client
        team_slug: Optional[str]
            Team slug of the team the dataset will belong to. Defaults to None.


        Returns
        -------
        Client
            The initialized client.
        """
        if not config_path.exists():
            raise MissingConfig()
        config = Config(config_path)

        return cls(config=config, default_team=team_slug)

    @classmethod
    def from_guest(cls, datasets_dir: Optional[Path] = None) -> "Client":
        """
        Factory method to create a client and access datasets as a guest.

        Parameters
        ----------
        datasets_dir : Optional[Path]
            String where the client should be initialized from (aka the root path). Defaults to None.

        Returns
        -------
        Client
            The initialized client.
        """
        if datasets_dir is None:
            datasets_dir = Path.home() / ".darwin" / "datasets"

        config: Config = Config(path=None)
        config.set_global(api_endpoint=Client.default_api_url(), base_url=Client.default_base_url())

        return cls(config=config)

    @classmethod
    def from_api_key(cls, api_key: str, datasets_dir: Optional[Path] = None) -> "Client":
        """
        Factory method to create a client given an API key.

        Parameters
        ----------
        api_key: str
            API key to use to authenticate the client
        datasets_dir : Optional[Path]
            String where the client should be initialized from (aka the root path). Defaults to None.

        Returns
        -------
        Client
            The initialized client.
        """
        if not datasets_dir:
            datasets_dir = Path.home() / ".darwin" / "datasets"

        headers: Dict[str, str] = {"Content-Type": "application/json", "Authorization": f"ApiKey {api_key}"}
        api_url: str = Client.default_api_url()
        response: requests.Response = requests.get(urljoin(api_url, "/users/token_info"), headers=headers)

        if not response.ok:
            raise InvalidLogin()

        data: Dict[str, Any] = response.json()
        team: str = data["selected_team"]["slug"]

        config: Config = Config(path=None)
        config.set_team(team=team, api_key=api_key, datasets_dir=str(datasets_dir))
        config.set_global(api_endpoint=api_url, base_url=Client.default_base_url())

        return cls(config=config, default_team=team)

    @staticmethod
    def default_api_url() -> str:
        """
        Returns the default api url.

        Returns
        -------
        str
            The default api url.
        """
        return f"{Client.default_base_url()}/api/"

    @staticmethod
    def default_base_url() -> str:
        """
        Returns the default base url.

        Returns
        -------
        str
            The default base url.
        """
        return os.getenv("DARWIN_BASE_URL", "https://darwin.v7labs.com")

    def _get_headers(self, team_slug: Optional[str] = None, compressed: bool = False) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}

        api_key: Optional[str] = None
        team_config: Optional[Team] = self.config.get_team(team_slug or self.default_team, raise_on_invalid_team=False)

        if team_config:
            api_key = team_config.api_key

        if api_key and len(api_key) > 0:
            headers["Authorization"] = f"ApiKey {api_key}"

        if compressed:
            headers["X-Darwin-Payload-Compression-Version"] = "1"

        from darwin import __version__

        headers["User-Agent"] = f"darwin-py/{__version__}"
        return headers

    def _get_raw_from_full_url(
        self, url: str, team_slug: Optional[str] = None, retry: bool = False, stream: bool = False
    ) -> Response:
        response: Response = self.session.get(url, headers=self._get_headers(team_slug), stream=stream)

        self.log.debug(
            f"Client GET request response ({get_response_content(response)}) with status "
            f"({response.status_code}). "
            f"Client: ({self})"
            f"Request: (url={url})"
        )

        self._raise_if_known_error(response, url)

        if not response.ok and retry:
            time.sleep(10)
            return self._get_raw_from_full_url(url=url, team_slug=team_slug, retry=False, stream=stream)

        response.raise_for_status()

        return response

    def _get_raw(
        self, endpoint: str, team_slug: Optional[str] = None, retry: bool = False, stream: bool = False
    ) -> Response:
        return self._get_raw_from_full_url(urljoin(self.url, endpoint), team_slug, retry=retry, stream=stream)

    def _get(
        self, endpoint: str, team_slug: Optional[str] = None, retry: bool = False
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        response = self._get_raw(endpoint, team_slug, retry)
        return self._decode_response(response)

    def _put_raw(
        self, endpoint: str, payload: Dict[str, Any], team_slug: Optional[str] = None, retry: bool = False
    ) -> Response:
        response: requests.Response = self.session.put(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers(team_slug)
        )

        self.log.debug(
            f"Client PUT request got response ({get_response_content(response)}) with status "
            f"({response.status_code}). "
            f"Client: ({self})"
            f"Request: (endpoint={endpoint}, payload={payload})"
        )

        self._raise_if_known_error(response, urljoin(self.url, endpoint))

        if not response.ok and retry:
            time.sleep(10)
            return self._put_raw(endpoint, payload=payload, retry=False)

        response.raise_for_status()

        return response

    def _put(
        self, endpoint: str, payload: Dict[str, Any], team_slug: Optional[str] = None, retry: bool = False
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        response: Response = self._put_raw(endpoint, payload, team_slug, retry)
        return self._decode_response(response)

    def _post_raw(
        self,
        endpoint: str,
        payload: Optional[Dict[Any, Any]] = None,
        team_slug: Optional[str] = None,
        retry: bool = False,
    ) -> Response:
        if payload is None:
            payload = {}

        compression_level = int(self.config.get("global/payload_compression_level", "0"))

        if compression_level > 0:
            compressed_payload = zlib.compress(json.dumps(payload).encode("utf-8"), level=compression_level)

            response: Response = requests.post(
                urljoin(self.url, endpoint),
                data=compressed_payload,
                headers=self._get_headers(team_slug, compressed=True),
            )
        else:
            response: Response = requests.post(
                urljoin(self.url, endpoint), json=payload, headers=self._get_headers(team_slug)
            )

        self.log.debug(
            f"Client POST request response ({get_response_content(response)}) with unexpected status "
            f"({response.status_code}). "
            f"Client: ({self})"
            f"Request: (endpoint={endpoint}, payload={payload})"
        )

        self._raise_if_known_error(response, urljoin(self.url, endpoint))

        if not response.ok and retry:
            time.sleep(10)
            return self._post_raw(endpoint, payload=payload, retry=False)

        response.raise_for_status()

        return response

    def _post(
        self,
        endpoint: str,
        payload: Optional[Dict[Any, Any]] = None,
        team_slug: Optional[str] = None,
        retry: bool = False,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        response: Response = self._post_raw(endpoint, payload, team_slug, retry)
        return self._decode_response(response)

    def _delete(
        self,
        endpoint: str,
        payload: Optional[Dict[Any, Any]] = None,
        team_slug: Optional[str] = None,
        retry: bool = False,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        if payload is None:
            payload = {}

        response: requests.Response = self.session.delete(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers(team_slug)
        )

        self.log.debug(
            f"Client DELETE request response ({get_response_content(response)}) with unexpected status "
            f"({response.status_code}). "
            f"Client: ({self})"
            f"Request: (endpoint={endpoint})"
        )

        self._raise_if_known_error(response, urljoin(self.url, endpoint))

        if not response.ok and retry:
            time.sleep(10)
            return self._delete(endpoint, payload=payload, retry=False)

        response.raise_for_status()

        return self._decode_response(response)

    def _raise_if_known_error(self, response: Response, url: str) -> None:

        if response.status_code == 401:
            raise Unauthorized()

        if response.status_code == 404:
            raise NotFound(url)

        if response.status_code == 413:
            raise RequestEntitySizeExceeded(url)

        if has_json_content_type(response):
            body = response.json()
            is_name_taken: Optional[bool] = None
            if isinstance(body, Dict):
                errors = body.get("errors")
                if errors and isinstance(errors, list):
                    for error in errors:
                        # we haven't really implemented this yet
                        pass
                if errors and isinstance(errors, Dict):
                    is_name_taken = errors.get("name") == ["has already been taken"]

            if response.status_code == 422:
                if is_name_taken:
                    raise NameTaken
                raise ValidationError(body)

        if response.status_code == 429:
            error_code: Optional[str] = None
            try:
                error_code = response.json()["errors"]["code"]
            except:
                pass

            if error_code == "INSUFFICIENT_REMAINING_STORAGE":
                raise InsufficientStorage()

    def _decode_response(self, response: requests.Response) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Decode the response as JSON entry or return a dictionary with the error

        Parameters
        ----------
        response: requests.Response
            Response to decode
        debug : bool
            Debugging flag. In this case failed requests get printed

        Returns
        -------
        dict
        JSON decoded entry or error
        """

        if "latest-darwin-py" in response.headers:
            self._handle_latest_darwin_py(response.headers["latest-darwin-py"])

        try:
            return response.json()
        except ValueError:
            self.log.error(f"[ERROR {response.status_code}] {response.text}")
            response.close()
            return {"error": "Response is not JSON encoded", "status_code": response.status_code, "text": response.text}

    def _handle_latest_darwin_py(self, server_latest_version: str) -> None:
        try:

            def parse_version(version: str) -> DarwinVersionNumber:
                (major, minor, patch) = version.split(".")
                return (int(major), int(minor), int(patch))

            from darwin import __version__

            current_version = parse_version(__version__)
            latest_version = parse_version(server_latest_version)
            if current_version >= latest_version:
                return
            self._newer_version = latest_version
        except:
            pass

    @property
    def newer_darwin_version(self) -> Optional[DarwinVersionNumber]:
        return self._newer_version

    def __str__(self) -> str:
        return f"Client(default_team={self.default_team})"

    @property
    def api_v2(self):
        return BackendV2(self, self.config.get_default_team().slug)
