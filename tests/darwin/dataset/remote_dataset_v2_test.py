import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from darwin.client import BackendV2, Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.release import Release
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from tests.fixtures import *


@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug, "api_key"], "mock_api_key")
    config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    return Client(config)


@pytest.fixture
def remote_dataset(darwin_client: Client, dataset_name: str, dataset_slug: str, team_slug: str):
    return RemoteDatasetV2(client=darwin_client, team=team_slug, name=dataset_name, slug=dataset_slug, dataset_id=1)


@pytest.mark.usefixtures("file_read_write_test")
def describe_create_annotation_group():
    def calls_api(remote_dataset: RemoteDataset):
        id = uuid.uuid4()
        with patch.object(BackendV2, "create_annotation_group", return_value={"id": id}) as stub:
            remote_dataset.create_annotation_group("ann-group")
            stub.assert_called_once_with(
                payload={
                    "dataset_id": remote_dataset.dataset_id,
                    "name": "ann-group",
                },
            )


@pytest.mark.usefixtures("file_read_write_test")
def describe_get_or_create_ground_truth():
    def returns_existing_id_if_existing(remote_dataset: RemoteDataset):
        id = uuid.uuid4()
        with patch.object(
            BackendV2, "list_ground_truths", return_value={"ground_truths": [{"id": id}]}
        ) as list_stub, patch.object(BackendV2, "create_ground_truth") as create_stub:
            got_id = remote_dataset.get_or_create_ground_truth()
            assert got_id == id

            list_stub.assert_called_once_with(remote_dataset.slug)
            create_stub.assert_not_called()

    def creates_new_if_no_existing_ground_truth(remote_dataset: RemoteDataset):
        id = uuid.uuid4()
        with patch.object(
            BackendV2, "list_ground_truths", return_value={"ground_truths": []}
        ) as list_stub, patch.object(BackendV2, "create_ground_truth", return_value={"id": id}) as create_stub:
            got_id = remote_dataset.get_or_create_ground_truth()
            assert got_id == id

            list_stub.assert_called_once_with(remote_dataset.slug)
            create_stub.assert_called_once_with(remote_dataset.slug, remote_dataset.name)


@pytest.mark.usefixtures("file_read_write_test")
def describe_begin_evaluation_run():
    def calls_api(remote_dataset: RemoteDataset):
        id = uuid.uuid4()
        with patch.object(BackendV2, "begin_evaluation_run", return_value={"id": id}) as stub:
            ground_truth_id = str(uuid.uuid4())
            predictions_annotation_group_id = str(uuid.uuid4())

            remote_dataset.begin_evaluation_run(ground_truth_id, predictions_annotation_group_id, "my-run")
            stub.assert_called_once_with(
                remote_dataset.slug, ground_truth_id, predictions_annotation_group_id, "my-run"
            )
