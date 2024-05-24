from typing import Dict

import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.set_item_layout import set_item_layout
from darwin.future.data_objects.item import ItemLayout
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.core.items.fixtures import *


@responses.activate
def test_set_item_layout_returns_blank_object(
    base_client: ClientCore, base_layout: ItemLayout
) -> None:
    dataset_ids = [1, 2, 3]
    params = {"param1": "value1", "param2": "value2"}
    team_slug = "my_team"
    responses.add(
        responses.POST,
        f"{base_client.config.api_endpoint}v2/teams/{team_slug}/items/layout",
        json={"affected_item_count": 2},
        status=200,
    )

    response = set_item_layout(base_client, team_slug, dataset_ids, base_layout, params)

    assert response == {"affected_item_count": 2}


@responses.activate
def test_set_item_layout_raises_on_incorrect_parameters(
    base_client: ClientCore, base_layout: ItemLayout
) -> None:
    team_slug = "my_team"
    dataset_ids = [1, 2, 3]
    params: Dict[str, UnknownType] = {}

    with pytest.raises(AssertionError):
        set_item_layout(base_client, team_slug, dataset_ids, base_layout, params)


@responses.activate
def test_set_item_layout_raises_on_4xx_status_code(
    base_client: ClientCore, base_layout: ItemLayout
) -> None:
    team_slug = "my_team"
    dataset_ids = [1, 2, 3]
    params = {"param1": "value1", "param2": "value2"}

    responses.add(
        responses.POST,
        f"{base_client.config.api_endpoint}v2/teams/{team_slug}/items/layout",
        json={"error": "Bad Request"},
        status=400,
    )

    with pytest.raises(BadRequest):
        set_item_layout(base_client, team_slug, dataset_ids, base_layout, params)


@responses.activate
def test_set_item_layout_sends_correct_payload(
    base_client: ClientCore, base_layout: ItemLayout
) -> None:
    team_slug = "my_team"
    dataset_ids = [1, 2, 3]
    params = {"param1": "value1", "param2": "value2"}

    responses.add(
        responses.POST,
        f"{base_client.config.api_endpoint}v2/teams/{team_slug}/items/layout",
        json={},
        status=200,
        match=[
            responses.json_params_matcher(
                {
                    "filters": {"dataset_ids": dataset_ids, **params},
                    "layout": dict(base_layout),
                }
            )
        ],
    )

    set_item_layout(base_client, team_slug, dataset_ids, base_layout, params)
