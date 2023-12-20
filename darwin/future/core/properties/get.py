from typing import List, Optional, Union
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.properties import FullProperty


def get_team_properties(
    client: ClientCore,
    team_slug: Optional[str] = None,
    params: Optional[QueryString] = None,
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
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/properties", query_string=params)
    assert isinstance(response, dict)
    return [FullProperty.model_validate(item) for item in response["properties"]]


def get_team_full_properties(
    client: ClientCore,
    team_slug: Optional[str] = None,
    params: Optional[QueryString] = None,
) -> List[FullProperty]:
    params = (
        params + QueryString({"include_values": True})
        if params and not params.get("include_values")
        else QueryString({"include_values": True})
    )
    return get_team_properties(client, team_slug, params)


def get_property_by_id(
    client: ClientCore, property_id: Union[str, UUID], team_slug: Optional[str] = None
) -> FullProperty:
    """
    Returns a FullProperty object for the specified team slug.

    Parameters:
        client (ClientCore): The client to use for the request.
        property_id (str | UUID): The ID of the property to get.
        team_slug (Optional[str]): The slug of the team to get. If not specified, the
            default team from the client's config will be used.

    Returns:
        FullProperty: FullProperty object from id

    Raises:
        HTTPError: If the response status code is not in the 200-299 range.
    """
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/properties/{str(property_id)}")
    assert isinstance(response, dict)
    return FullProperty.model_validate(response)
