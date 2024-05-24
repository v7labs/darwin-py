import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.assign_items import assign_items
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_assign_items(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    assignee_id = 123456
    workflow_id = "123456"
    item_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    filters = {"item_ids": item_ids}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/assign",
        json={"created_commands": 1},
        status=200,
    )

    response = assign_items(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        assignee_id=assignee_id,
        workflow_id=workflow_id,
        filters=filters,
    )

    assert response == {"created_commands": 1}


@responses.activate
def test_assign_items_filters_error(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    assignee_id = 123456
    workflow_id = "123456"
    filters = {}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/assign",
        json={"created_commands": 1},
        status=200,
    )

    with pytest.raises(AssertionError) as excinfo:
        assign_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            assignee_id=assignee_id,
            workflow_id=workflow_id,
            filters=filters,
        )
    (msg,) = excinfo.value.args
    assert (
        msg
        == "No parameters provided, please provide at least one non-dataset id filter"
    )


@responses.activate
def test_assign_items_bad_request_error(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    assignee_id = 123456
    workflow_id = "123456"
    item_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    filters = {"item_ids": item_ids}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/assign",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        assign_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            assignee_id=assignee_id,
            workflow_id=workflow_id,
            filters=filters,
        )
