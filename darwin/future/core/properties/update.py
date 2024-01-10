from typing import Optional, Union

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONDict
from darwin.future.data_objects.properties import FullProperty, PropertyValue


def update_property(
    client: ClientCore,
    params: Union[FullProperty, JSONDict],
    team_slug: Optional[str] = None,
) -> FullProperty:
    """
    Updates a property for the specified team slug.

    Parameters:
        client (ClientCore): The client to use for the request.
        team_slug (Optional[str]): The slug of the team to get. If not specified, the
            default team from the client's config will be used.
        params (Optional[JSONType]): The JSON data to use for the request.

    Returns:
        FullProperty: FullProperty object for the created property.

    Raises:
        HTTPError: If the response status code is not in the 200-299 range.
    """
    if not team_slug:
        team_slug = client.config.default_team
    if isinstance(params, FullProperty):
        id, params = params.to_update_endpoint()
    else:
        id = params.get("id")
        del params["id"]
    response = client.put(f"/v2/teams/{team_slug}/properties/{id}", data=params)
    assert isinstance(response, dict)
    return FullProperty.model_validate(response)


def update_property_value(
    client: ClientCore,
    params: Union[PropertyValue, JSONDict],
    item_id: str,
    team_slug: Optional[str] = None,
) -> PropertyValue:
    """
    Updates a property value for the specified property id.

    Parameters:
        client (ClientCore): The client to use for the request.
        team_slug (Optional[str]): The slug of the team to get. If not specified, the
            default team from the client's config will be used.
        params (Optional[JSONType]): The JSON data to use for the request.

    Returns:
        FullProperty: FullProperty object for the created property.

    Raises:
        HTTPError: If the response status code is not in the 200-299 range.
    """
    if not team_slug:
        team_slug = client.config.default_team
    if isinstance(params, PropertyValue):
        id, params = params.to_update_endpoint()
    else:
        id = params.get("id")
        del params["id"]
    response = client.put(
        f"/v2/teams/{team_slug}/properties/{item_id}/property_values/{id}", data=params
    )
    assert isinstance(response, dict)
    return PropertyValue.model_validate(response)
