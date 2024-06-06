from pathlib import Path
from typing import Tuple

import pytest

from darwin.future.core.client import ClientCore, DarwinConfig
from darwin.future.core.properties.create import create_property
from darwin.future.core.properties.get import (
    get_property_by_id,
    get_team_full_properties,
    get_team_properties,
)
from darwin.future.core.properties.update import update_property, update_property_value
from darwin.future.data_objects.properties import FullProperty, PropertyValue
from e2e_tests.objects import ConfigValues, E2EAnnotationClass
from e2e_tests.setup_tests import create_annotation_class


@pytest.fixture
def base_config(tmpdir: str) -> DarwinConfig:
    config = pytest.config_values
    assert config is not None
    assert isinstance(config, ConfigValues)
    server = config.server
    api_key = config.api_key
    team_slug = config.team_slug
    return DarwinConfig(
        api_key=api_key,
        base_url=server,
        api_endpoint=server + "/api/",
        datasets_dir=Path(tmpdir),
        default_team=team_slug,
        teams={},
    )


@pytest.fixture
def base_client(base_config: DarwinConfig) -> ClientCore:
    return ClientCore(base_config)


@pytest.fixture
def base_property_to_create() -> FullProperty:
    return FullProperty(
        id=None,
        name="test_property",
        type="single_select",
        description="",
        required=False,
        slug="test_property",
        team_id=None,
        annotation_class_id=None,
        options=None,
        property_values=[
            PropertyValue(
                id=None,
                position=None,
                type="string",
                value="test_value",
                color="rgba(100,100,100,1)",
            )
        ],
    )


def helper_create_annotation(name: str) -> Tuple[ConfigValues, E2EAnnotationClass]:
    config = pytest.config_values
    assert config is not None
    assert isinstance(config, ConfigValues)
    return config, create_annotation_class(name, "polygon", config)


def test_create_property(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation("test_for_create_property")

    # Actual test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    assert isinstance(output, FullProperty)


def test_get_team_properties(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation("test_for_get_properties")

    # Create a base property to use for the test
    # TODO: replace this with a fixture to isolate the test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    output.property_values = (
        None  # the base get_team_properties doesn't include property_values
    )
    assert isinstance(output, FullProperty)

    properties = get_team_properties(base_client, team_slug=config.team_slug)
    assert isinstance(properties, list)
    assert all(isinstance(property, FullProperty) for property in properties)
    assert len(properties) > 0

    for property in properties:
        if property.annotation_class_id == new_annotation_class.id:
            assert property == output
            break


def test_get_team_full_properties(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation(
        "test_for_get_full_properties"
    )

    # Create a base property to use for the test
    # TODO: replace this with a fixture to isolate the test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    assert isinstance(output, FullProperty)

    properties = get_team_full_properties(base_client, team_slug=config.team_slug)
    assert isinstance(properties, list)
    assert all(isinstance(property, FullProperty) for property in properties)
    assert len(properties) > 0

    for property in properties:
        if property.annotation_class_id == new_annotation_class.id:
            assert property == output
            break


def test_get_property_by_id(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation(
        "test_for_get_property_by_id"
    )

    # Create a base property to use for the test
    # TODO: replace this with a fixture to isolate the test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    assert isinstance(output, FullProperty)
    assert output.id is not None

    prop = get_property_by_id(base_client, output.id, team_slug=config.team_slug)
    assert isinstance(prop, FullProperty)
    assert output == prop


def test_update_property(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation("test_for_update_property")

    # Create a base property to use for the test
    # TODO: replace this with a fixture to isolate the test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    assert isinstance(output, FullProperty)
    assert output.id is not None

    assert output.property_values is not None
    output.property_values[0].value = "new_value"
    # default behaviour for update endpoint is to append the new value to the existing values
    new_output = update_property(base_client, output, team_slug=config.team_slug)
    assert isinstance(new_output, FullProperty)
    assert new_output.property_values is not None
    assert len(new_output.property_values) == 2
    assert new_output.property_values[1].value == output.property_values[0].value


def test_update_property_value(
    base_client: ClientCore, base_property_to_create: FullProperty
) -> None:
    config, new_annotation_class = helper_create_annotation(
        "test_for_update_property_value"
    )

    # Create a base property to use for the test
    # TODO: replace this with a fixture to isolate the test
    base_property_to_create.annotation_class_id = new_annotation_class.id
    output = create_property(
        base_client, base_property_to_create, team_slug=config.team_slug
    )
    assert isinstance(output, FullProperty)
    assert output.id is not None

    assert output.property_values is not None
    id = output.id
    pv = output.property_values[0]
    pv.value = "new_value"
    new_output = update_property_value(
        base_client, pv, item_id=id, team_slug=config.team_slug
    )
    assert isinstance(new_output, PropertyValue)
    assert pv == new_output


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
