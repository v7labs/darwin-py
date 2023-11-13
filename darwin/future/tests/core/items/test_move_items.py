from uuid import UUID

import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.move_items import move_items_to_stage
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_move_items_to_stage_including_filters(base_client: ClientCore) -> None:
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
    workflow_id = UUID("00000000-0000-0000-0000-000000000000")
    stage_id = UUID("00000000-0000-0000-0000-000000000000")

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/stage",
        json={"affected_item_count": 2},
        status=200,
    )

    response = move_items_to_stage(
        client=base_client,
        team_slug=team_slug,
        workflow_id=workflow_id,
        dataset_ids=dataset_ids,
        stage_id=stage_id,
        filters=filters,
    )

    assert response == {"affected_item_count": 2}


@responses.activate
def test_move_items_to_stage_raises_on_incorrect_parameters(
    base_client: ClientCore,
) -> None:
    dataset_ids = [1, 2, 3]
    team_slug = "test-team"
    workflow_id = UUID("00000000-0000-0000-0000-000000000000")
    stage_id = UUID("00000000-0000-0000-0000-000000000000")

    with pytest.raises(AssertionError):
        move_items_to_stage(
            client=base_client,
            team_slug=team_slug,
            workflow_id=workflow_id,
            dataset_ids=dataset_ids,
            stage_id=stage_id,
        )


@responses.activate
def test_move_items_to_stage_with_error_response(base_client: ClientCore) -> None:
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
    workflow_id = UUID("00000000-0000-0000-0000-000000000000")
    stage_id = UUID("00000000-0000-0000-0000-000000000000")

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/stage",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        move_items_to_stage(
            client=base_client,
            team_slug=team_slug,
            workflow_id=workflow_id,
            dataset_ids=dataset_ids,
            stage_id=stage_id,
            filters=filters,
        )
