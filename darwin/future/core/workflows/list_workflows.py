from typing import List, Optional, Tuple

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WorkflowCore, WorkflowListValidator


def list_workflows(
    client: ClientCore, team_slug: Optional[str] = None
) -> Tuple[List[WorkflowCore], List[Exception]]:
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
    workflows: List[WorkflowCore] = []

    try:
        team_slug = team_slug or client.config.default_team
        response = client.get(f"/v2/teams/{team_slug}/workflows?worker=false")
        list_of_workflows = WorkflowListValidator(list=response)  # type: ignore
        workflows = [
            WorkflowCore.model_validate(workflow) for workflow in list_of_workflows.list
        ]
    except Exception as e:
        exceptions.append(e)

    return workflows, exceptions
