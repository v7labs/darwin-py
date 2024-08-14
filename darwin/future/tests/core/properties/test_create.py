import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.properties import create_property
from darwin.future.data_objects.properties import FullProperty
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_create_property(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.POST,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties",
        json=base_property_object.model_dump(mode="json"),
        status=200,
    )
    # Call the function being tested
    property = create_property(
        base_client,
        params=base_property_object,
        team_slug=base_client.config.default_team,
    )

    # Assertions
    assert isinstance(property, FullProperty)
    assert property == base_property_object


@responses.activate
def test_create_property_from_json(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    json = base_property_object.to_create_endpoint()
    # Mocking the response using responses library
    responses.add(
        responses.POST,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties",
        json=base_property_object.model_dump(mode="json"),
        status=200,
    )
    # Call the function being tested
    property = create_property(
        base_client, params=json, team_slug=base_client.config.default_team
    )

    # Assertions
    assert isinstance(property, FullProperty)
    assert property == base_property_object
