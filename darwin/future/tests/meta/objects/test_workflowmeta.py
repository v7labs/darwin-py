import pytest
import responses
from responses import json_params_matcher

from darwin.future.tests.meta.objects.fixtures import *


def test_item_set_stage_stage_object(workflow: Workflow) -> None:
    with responses.RequestsMock() as rsps:
        stages = workflow.stages.collect()
        items = workflow.items.collect()
        item = items[0]
        stage = stages[0]

        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        workflow_id = workflow.meta_params["workflow_id"]
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
