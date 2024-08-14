import responses
from responses.matchers import query_param_matcher

from darwin.future.core.client import ClientCore
from darwin.future.core.properties import (
    get_property_by_id,
    get_team_full_properties,
    get_team_properties,
)
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.properties import FullProperty
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_get_team_properties(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    base_property_object.options = None
    base_property_object.property_values = None
    response_data = {"properties": [base_property_object.model_dump(mode="json")]}
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    properties = get_team_properties(base_client)

    # Assertions
    assert isinstance(properties, list)
    assert all(isinstance(property, FullProperty) for property in properties)
    assert properties[0] == base_property_object


@responses.activate
def test_get_team_full_properties(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    response_data = {"properties": [base_property_object.model_dump(mode="json")]}
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties",
        match=[
            query_param_matcher({"include_values": "true"}),
        ],
        json=response_data,
        status=200,
    )
    params = QueryString({"include_values": True})
    # Call the function being tested
    properties = get_team_full_properties(base_client, params=params)

    # Assertions
    assert isinstance(properties, list)
    assert all(isinstance(property, FullProperty) for property in properties)
    assert properties[0] == base_property_object


@responses.activate
def test_get_property_by_id(
    base_client: ClientCore, base_property_object: FullProperty
) -> None:
    # Mocking the response using responses library
    property_id = "0"
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/properties/{property_id}",
        json=base_property_object.model_dump(mode="json"),
        status=200,
    )

    # Call the function being tested
    property = get_property_by_id(base_client, property_id)

    # Assertions
    assert isinstance(property, FullProperty)
    assert property == base_property_object
