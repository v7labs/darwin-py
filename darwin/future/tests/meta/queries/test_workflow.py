from collections import namedtuple
from datetime import datetime, timezone

import responses

from darwin.future.core.client import ClientCore
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.meta.queries.workflow import WorkflowQuery
from darwin.future.tests.core.fixtures import *

WORKFLOW_1 = "6dca86a3-48fb-40cc-8594-88310f5f1fdf"
WORKFLOW_2 = "e34fe935-4a1c-4231-bb55-454e2ac7673f"
WORKFLOW_3 = "45cf0abe-58a2-4878-b171-4fb5421a1c39"


def workflows_query_endpoint(team: str) -> str:
    return f"v2/teams/{team}/workflows?worker=false"


@responses.activate
def test_workflowquery_collects_basic(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, [])
    workflows = query._collect()

    assert len(workflows) == 3
    assert all(isinstance(workflow, Workflow) for workflow in workflows.values())


@responses.activate
def test_workflowquery_filters_uuid(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "id",
            "param": "6dca86a3-48fb-40cc-8594-88310f5f1fdf",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 1
    assert str(workflows[0].id) == WORKFLOW_1


@responses.activate
def test_workflowquery_filters_inserted_at(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    start = "2021-06-01T15:00:00.000+00:00"
    end = "2021-06-04T15:00:00.000+00:00"

    query = (
        WorkflowQuery(base_client, [])
        .where(
            {
                "name": "inserted_at_start",
                "param": start,
            }
        )
        .where(
            {
                "name": "inserted_at_end",
                "param": end,
            }
        )
    )
    workflows = query._collect()

    assert len(workflows) == 2
    ids = [str(workflow.id) for workflow in workflows.values()]
    assert WORKFLOW_1 in ids
    assert WORKFLOW_2 in ids


@responses.activate
def test_workflowquery_filters_updated_at(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    start = "2021-06-04T15:00:00.000+00:00"
    end = "2021-06-06T15:00:00.000+00:00"

    query = (
        WorkflowQuery(base_client, [])
        .where(
            {
                "name": "updated_at_start",
                "param": start,
            }
        )
        .where(
            {
                "name": "updated_at_end",
                "param": end,
            }
        )
    )
    workflows = query._collect()

    assert len(workflows) == 2
    ids = [str(workflow.id) for workflow in workflows.values()]
    assert WORKFLOW_1 in ids
    assert WORKFLOW_2 in ids


@responses.activate
def test_workflowquery_filters_dataset_id(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "dataset_id",
            "param": "1",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 1
    assert str(workflows[0].id) == WORKFLOW_1


@responses.activate
def test_workflowquery_filters_dataset_id_multiple_ids(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "dataset_id",
            "param": "1,2",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 2
    assert str(workflows[0].id) == WORKFLOW_1
    assert str(workflows[1].id) == WORKFLOW_2


@responses.activate
def test_workflowquery_filters_dataset_name(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "dataset_name",
            "param": "test-dataset-1",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 1
    assert str(workflows[0].id) == WORKFLOW_1


@responses.activate
def test_workflowquery_filters_dataset_name_mutliple_names(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "dataset_name",
            "param": "test-dataset-1,test-dataset-2",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 2
    assert str(workflows[0].id) == WORKFLOW_1
    assert str(workflows[1].id) == WORKFLOW_2


@responses.activate
def test_workflowquery_filters_stages(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)

    query = WorkflowQuery(base_client, []).where(
        {
            "name": "has_stages",
            "param": "5445adcb-193d-4f76-adb0-0c6d5f5e4c04",
        }
    )
    workflows = query._collect()

    assert len(workflows) == 1
    assert str(workflows[0].name) == "test-workflow-3"


@responses.activate
def test_workflowquery_filters_stages_multiple(
    base_client: ClientCore, base_filterable_workflows: dict
) -> None:
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(
        base_client.config.default_team
    )
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)
    param = "5445adcb-193d-4f76-adb0-0c6d5f5e4c04,53d2c997-6bb0-4766-803c-3c8d1fb21072"
    query = WorkflowQuery(base_client, []).where(
        {
            "name": "has_stages",
            "param": param,
        }
    )
    workflows = query._collect()

    assert len(workflows) == 2
    workflow_names = [workflow.name for workflow in workflows.values()]

    assert "test-workflow-3" in workflow_names
    assert "test-workflow-1" in workflow_names


# Test static methods
def test__date_compare() -> None:
    date1 = datetime(1970, 1, 1, 0, 0, 0, 1, timezone.utc)
    date1_copy = datetime(1970, 1, 1, 0, 0, 0, 1, timezone.utc)
    date2 = datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc)

    assert WorkflowQuery._date_compare(date1, date2)
    assert WorkflowQuery._date_compare(date1, date1_copy)
    assert not WorkflowQuery._date_compare(date2, date1)


def test__stages_contains() -> None:
    FakeStage = namedtuple("FakeStage", ["id"])
    stages = [
        FakeStage("1"),
        FakeStage("2"),
        FakeStage("3"),
    ]

    assert WorkflowQuery._stages_contains(stages, "1")  # type: ignore
    assert WorkflowQuery._stages_contains(stages, "2")  # type: ignore
    assert WorkflowQuery._stages_contains(stages, "3")  # type: ignore
    assert not WorkflowQuery._stages_contains(stages, "4")  # type: ignore
