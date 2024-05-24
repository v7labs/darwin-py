import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_set_item_priority_including_filters(base_client: ClientCore) -> None:
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
    priority = 100

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/priority",
        json={"affected_item_count": 2},
        status=200,
    )

    response = set_item_priority(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        filters=filters,
        priority=priority,
    )

    assert response == {"affected_item_count": 2}


@responses.activate
def test_set_item_priority_raises_on_incorrect_parameters(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    priority = 100

    with pytest.raises(AssertionError):
        set_item_priority(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            priority=priority,
        )


@responses.activate
def test_set_item_priority_with_error_response(base_client: ClientCore) -> None:
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
    priority = 100

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/priority",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        set_item_priority(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            filters=filters,
            priority=priority,
        )
