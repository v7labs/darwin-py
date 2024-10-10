import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.properties import update_property, update_property_value
from darwin.future.data_objects.properties import FullProperty, PropertyValue
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_update_property(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.PUT,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties/{base_property_object.id}",
        json=base_property_object.model_dump(mode="json"),
        status=200,
    )
    # Call the function being tested
    property = update_property(
        base_client,
        params=base_property_object,
        team_slug=base_client.config.default_team,
    )

    # Assertions
    assert isinstance(property, FullProperty)
    assert property == base_property_object


@responses.activate
def test_update_property_value(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    item_id = base_property_object.id
    assert item_id
    assert base_property_object.property_values
    pv = base_property_object.property_values[0]
    responses.add(
        responses.PUT,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties/{item_id}/property_values/{pv.id}",
        json=pv.model_dump(),
        status=200,
    )
    # Call the function being tested
    property_value = update_property_value(
        base_client,
        params=pv,
        item_id=item_id,
        team_slug=base_client.config.default_team,
    )

    # Assertions
    assert isinstance(property_value, PropertyValue)
    assert property_value == pv
