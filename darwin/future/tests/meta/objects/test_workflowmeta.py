import responses
from responses import json_params_matcher
from responses.matchers import query_param_matcher

from darwin.future.meta.objects.workflow import Workflow
from darwin.future.tests.meta.objects.fixtures import *


def test_item_set_stage_with_stage_object(
    workflow: Workflow,
    base_single_workflow_object: list,
    base_items_json_response: dict,
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            workflow.client.config.api_endpoint
            + f"v2/teams/default-team/workflows/{workflow.id}",
            status=200,
            json=base_single_workflow_object,
        )
        stages = workflow.stages.collect()
        rsps.add(
            rsps.GET,
            workflow.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {
                        "page[offset]": "0",
                        "page[size]": "500",
                        "dataset_ids": "101",
                    }
                )
            ],
            status=200,
            json=base_items_json_response,
        )
        items = workflow.items.collect()
        item = items[0]
        stage = stages[0]

        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        workflow_id = str(workflow.id)
        stage_id = str(stage.id)
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/stage",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "stage_id": stage_id,
                        "workflow_id": workflow_id,
                    }
                )
            ],
            json={},
        )
        item.set_stage(stage)
