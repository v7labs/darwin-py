from typing import List, Optional

from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.properties import FullProperty


def get_all_properties(
    client: ClientCore, team_slug: Optional[str] = None
) -> List[FullProperty]:
    """
    Returns a TeamCore object for the specified team slug.

    Parameters:
        client (ClientCore): The client to use for the request.
        team_slug (Optional[str]): The slug of the team to get. If not specified, the
            default team from the client's config will be used.

    Returns:
        TeamCore: The TeamCore object for the specified team slug.

    Raises:
        HTTPError: If the response status code is not in the 200-299 range.
    """
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/properties")
    assert isinstance(response, dict)
    return parse_obj_as(List[FullProperty], response.get("properties"))
