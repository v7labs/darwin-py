from typing import Dict

import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_delete_items_including_filters(base_client: ClientCore) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    filters: Dict[str, UnknownType] = {
        "not_statuses": ["uploading", "annotate"],
        "not_assignees": [123, 456, 789],
        "item_ids": [
            ("00000000-0000-0000-0000-000000000000"),
            ("00000000-0000-0000-0000-000000000000"),
        ],
    }

    responses.add(
        responses.DELETE,
        base_client.config.api_endpoint + "v2/teams/test-team/items",
        json={"affected_item_count": 2},
        status=200,
    )

    response = delete_list_of_items(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        filters=filters,
    )

    assert response == {"affected_item_count": 2}


@responses.activate
def test_delete_items_raises_on_incorrect_parameters(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    filters: Dict[str, UnknownType] = {}

    with pytest.raises(AssertionError):
        delete_list_of_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            filters=filters,
        )


@responses.activate
def test_delete_items_with_error_response(base_client: ClientCore) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    filters: Dict[str, UnknownType] = {
        "not_statuses": ["uploading", "annotate"],
        "not_assignees": [123, 456, 789],
        "item_ids": [
            ("00000000-0000-0000-0000-000000000000"),
            ("00000000-0000-0000-0000-000000000000"),
        ],
    }

    responses.add(
        responses.DELETE,
        base_client.config.api_endpoint + "v2/teams/test-team/items",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        delete_list_of_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            filters=filters,
        )
