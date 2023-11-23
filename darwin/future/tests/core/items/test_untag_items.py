import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.untag_items import untag_items
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_untag_items(base_client: ClientCore) -> None:
    team_slug = "test-team"
    dataset_ids = [1, 2, 3]
    tag_id = "123456"
    item_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    filters = {"item_ids": item_ids}

    responses.add(
        responses.DELETE,
        base_client.config.api_endpoint + "v2/teams/test-team/items/slots/tags",
        json={"created_commands": 2},
        status=200,
    )

    response = untag_items(
        client=base_client,
        team_slug=team_slug,
        dataset_ids=dataset_ids,
        tag_id=tag_id,
        filters=filters,
    )

    assert response == {"created_commands": 2}
