from typing import List, Optional

from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WorkflowCore


def get_workflows(client: ClientCore, team_slug: Optional[str] = None) -> List[WorkflowCore]:
    team_slug = team_slug or client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/workflows?worker=false")

    return [parse_obj_as(WorkflowCore, workflow) for workflow in response]
