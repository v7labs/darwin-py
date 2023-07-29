from typing import List, Optional

from pydantic import parse_obj_as

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.workflow import WorkflowModel


def get_workflows(client: CoreClient, team_slug: Optional[str] = None) -> List[WorkflowModel]:
    team_slug = team_slug or client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/workflows?worker=false")

    return [parse_obj_as(WorkflowModel, workflow) for workflow in response]
