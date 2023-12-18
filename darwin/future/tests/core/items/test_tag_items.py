from typing import Dict

import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.tag_items import tag_items
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_tag_items(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    tag_id = 123456
    item_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    filters = {"item_ids": item_ids}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/slots/tags",
        json={"created_commands": 2},
        status=200,
    )

    response = tag_items(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        tag_id=tag_id,
        filters=filters,
    )

    assert response == {"created_commands": 2}


@responses.activate
def test_tag_items_empty_filters_error(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    tag_id = 123456
    # this should raise an error as no filters are provided
    filters: Dict[str, UnknownType] = {}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/slots/tags",
        json={"created_commands": 2},
        status=200,
    )

    with pytest.raises(AssertionError) as excinfo:
        tag_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            tag_id=tag_id,
            filters=filters,
        )
    (msg,) = excinfo.value.args
    assert (
        msg
        == "No parameters provided, please provide at least one non-dataset id filter"
    )


@responses.activate
def test_tag_items_bad_request_error(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    tag_id = "123456"
    item_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    filters = {"item_ids": item_ids}

    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/slots/tags",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        tag_items(
            client=base_client,
            team_slug=team_slug,
            dataset_ids=dataset_ids,
            tag_id=tag_id,  # type: ignore
            filters=filters,
        )
