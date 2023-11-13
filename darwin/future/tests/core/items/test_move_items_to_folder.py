import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_move_list_of_items_to_folder_including_filters(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    filters = {
        "not_statuses": ["uploading", "annotate"],
        "not_assignees": [123, 456, 789],
        "item_ids": [
            ("00000000-0000-0000-0000-000000000000"),
            ("00000000-0000-0000-0000-000000000000"),
        ],
    }
    path = "/test/path"

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/path",
        json={"affected_item_count": 2},
        status=200,
    )

    response = move_list_of_items_to_folder(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        filters=filters,
        path=path,
    )

    assert response == {"affected_item_count": 2}


@responses.activate
def test_move_list_of_items_to_folder_raises_on_incorrect_parameters(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    path = "/test/path"

    with pytest.raises(AssertionError):
        move_list_of_items_to_folder(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            path=path,
        )


@responses.activate
def test_move_list_of_items_to_folders_with_error_response(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    filters = {
        "not_statuses": ["uploading", "annotate"],
        "not_assignees": [123, 456, 789],
        "item_ids": [
            ("00000000-0000-0000-0000-000000000000"),
            ("00000000-0000-0000-0000-000000000000"),
        ],
    }
    path = "/test/path"

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/path",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        move_list_of_items_to_folder(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            path=path,
            filters=filters,
        )
