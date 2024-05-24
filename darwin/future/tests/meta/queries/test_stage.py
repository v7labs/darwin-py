import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WFTypeCore, WorkflowCore
from darwin.future.meta.objects.stage import Stage
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.meta.queries.stage import StageQuery
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def filled_query(base_client: ClientCore, base_workflow_meta: Workflow) -> StageQuery:
    return StageQuery(
        base_client, meta_params={"workflow_id": str(base_workflow_meta.id)}
    )


@pytest.fixture
def base_workflow_meta(
    base_client: ClientCore, base_single_workflow_object: dict
) -> Workflow:
    return Workflow(
        client=base_client,
        element=WorkflowCore.model_validate(base_single_workflow_object),
    )


@pytest.fixture
def multi_stage_workflow_object(base_single_workflow_object: dict) -> dict:
    stage = base_single_workflow_object["stages"][0]
    types = list(WFTypeCore.__members__.values()) * 3
    stages = []
    for i, t in enumerate(types):
        temp = stage.copy()
        temp["name"] = f"stage{i}"
        temp["type"] = t.value
        stages.append(temp)
    base_single_workflow_object["stages"] = stages
    return base_single_workflow_object


def test_WFTypes_accept_unknonwn() -> None:
    assert WFTypeCore("unknown") == WFTypeCore.UNKNOWN
    assert WFTypeCore("test") == WFTypeCore.UNKNOWN


def test_stage_collects_basic(
    filled_query: StageQuery,
    base_single_workflow_object: dict,
    base_workflow_meta: Workflow,
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = (
            filled_query.client.config.api_endpoint
            + f"v2/teams/default-team/workflows/{UUID}"
        )
        rsps.add(responses.GET, endpoint, json=base_single_workflow_object)
        stages = filled_query._collect()
        assert len(stages) == len(base_workflow_meta.stages)
        assert isinstance(stages[0], Stage)


def test_stage_filters_basic(
    filled_query: StageQuery,
    multi_stage_workflow_object: dict,
    base_workflow_meta: Workflow,
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = (
            filled_query.client.config.api_endpoint
            + f"v2/teams/default-team/workflows/{UUID}"
        )
        rsps.add(responses.GET, endpoint, json=multi_stage_workflow_object)
        stages = filled_query.where({"name": "name", "param": "stage1"})._collect()
        assert len(stages) == 1
        assert isinstance(stages[0], Stage)
        assert stages[0]._element.name == "stage1"


@pytest.mark.parametrize("wf_type", list(WFTypeCore.__members__.values()))
def test_stage_filters_WFType(
    wf_type: WFTypeCore,
    filled_query: StageQuery,
    multi_stage_workflow_object: dict,
    base_workflow_meta: Workflow,
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = (
            filled_query.client.config.api_endpoint
            + f"v2/teams/default-team/workflows/{UUID}"
        )
        rsps.add(responses.GET, endpoint, json=multi_stage_workflow_object)
        stages = filled_query.where({"name": "type", "param": wf_type.value})._collect()
        assert len(stages) == 3
        assert isinstance(stages[0], Stage)
        for key, stage in stages.items():
            assert stage._element.type == wf_type
