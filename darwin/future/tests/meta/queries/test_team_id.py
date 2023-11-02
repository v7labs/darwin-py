from uuid import UUID, uuid4

import responses
from responses.matchers import query_param_matcher

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.page import Page
from darwin.future.meta.objects.v7_id import V7ID
from darwin.future.meta.queries.item_id import ItemIDQuery
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def base_ItemIDQuery(base_client: ClientCore) -> ItemIDQuery:
    return ItemIDQuery(
        base_client, meta_params={"dataset_id": 0000, "team_slug": "test_team"}
    )


@pytest.fixture
def list_of_uuids() -> List[UUID]:
    return [uuid4() for _ in range(10)]


def test_pagination_collects_all(
    base_client: ClientCore, base_ItemIDQuery: ItemIDQuery, list_of_uuids: List[UUID]
) -> None:
    base_ItemIDQuery.page = Page(size=5)
    team_slug = base_ItemIDQuery.meta_params["team_slug"]
    dataset_id = base_ItemIDQuery.meta_params["dataset_id"]
    str_ids = [str(uuid) for uuid in list_of_uuids]
    with responses.RequestsMock() as rsps:
        endpoint = (
            base_client.config.api_endpoint + f"v2/teams/{team_slug}/items/list_ids"
        )
        rsps.add(
            responses.GET,
            endpoint,
            match=[
                query_param_matcher(
                    {
                        "page[offset]": "0",
                        "page[size]": "5",
                        "dataset_ids": str(dataset_id),
                    }
                )
            ],
            json={"item_ids": [str(uuid) for uuid in str_ids[:5]]},
        )
        rsps.add(
            responses.GET,
            endpoint,
            match=[
                query_param_matcher(
                    {
                        "page[offset]": "5",
                        "page[size]": "5",
                        "dataset_ids": str(dataset_id),
                    }
                )
            ],
            json={"item_ids": [str(uuid) for uuid in str_ids[5:]]},
        )
        rsps.add(
            responses.GET,
            endpoint,
            match=[
                query_param_matcher(
                    {
                        "page[offset]": "10",
                        "page[size]": "5",
                        "dataset_ids": str(dataset_id),
                    }
                )
            ],
            json={"item_ids": []},
        )

        ids = base_ItemIDQuery.collect_all()
        raw_ids = [x.id for x in ids]
        assert len(rsps.calls) == 3
        assert len(ids) == 10
        assert raw_ids == list_of_uuids
