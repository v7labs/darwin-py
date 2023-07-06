from typing import List, Optional, Tuple

from pydantic import ValidationError

from darwin.future.core.client import Client
from darwin.future.data_objects.workflow import Workflow, WorkflowListValidator


def list_workflows(client: Client, team_slug: Optional[str] = None) -> Tuple[List[Workflow], List[Exception]]:
    """
    Returns a list of workflows for the given team

    Parameters
    ----------
    client : Client
        The client to use to make the request
    team_slug : Optional[str]
        The slug of the team to retrieve workflows for

    Returns
    -------
    Tuple[List[Workflow], List[Exception]]
    """
    exceptions: List[Exception] = []
    workflows: List[Workflow] = []

    try:
        team_slug = team_slug or client.config.default_team
        response = client.get(f"/v2/teams/{team_slug}/workflows?worker=false")
        list_of_workflows = WorkflowListValidator(list=response)  # type: ignore
        workflows = [Workflow.parse_obj(workflow) for workflow in list_of_workflows.list]
    except Exception as e:
        exceptions.append(e)

    return workflows, exceptions
