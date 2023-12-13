from typing import Any, Dict, List, Mapping, Optional, Union

from attr import validate
from numpy import isin
from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONDict, JSONType
from darwin.future.data_objects.properties import FullProperty


def create_property(
    client: ClientCore,
    params: Union[Dict, FullProperty],
    team_slug: Optional[str] = None,
) -> List[FullProperty]:
    """
    Returns a List[FullProperty] object for the specified team slug.

    Parameters:
        client (ClientCore): The client to use for the request.
        team_slug (Optional[str]): The slug of the team to get. If not specified, the
            default team from the client's config will be used.

    Returns:
        List[FullProperty]: List of FullProperty objects for the specified team slug.

    Raises:
        HTTPError: If the response status code is not in the 200-299 range.
    """
    if isinstance(params, FullProperty):
        property = params
        params = property.dict()
    else:
        property = FullProperty(**params)
    assert property.validate_for_creation()
    if not team_slug:
        team_slug = client.config.default_team
    response = client.post(f"/v2/teams/{team_slug}/properties", data=params)
    assert isinstance(response, dict)
    return parse_obj_as(List[FullProperty], response.get("properties"))