from typing import Optional, Union

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONDict
from darwin.future.data_objects.properties import FullProperty


def create_property(
    client: ClientCore,
    params: Union[FullProperty, JSONDict],
    team_slug: Optional[str] = None,
) -> FullProperty:
    """
    Creates a property for the specified team slug.

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
        params = params.to_create_endpoint()
    response = client.post(f"/v2/teams/{team_slug}/properties", data=params)
    assert isinstance(response, dict)
    return FullProperty.model_validate(response)
