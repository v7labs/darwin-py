from typing import Dict, List

import pytest
import requests

from e2e_tests.exceptions import DataAlreadyExists, E2EException
from e2e_tests.helpers import api_call, generate_random_string
from e2e_tests.logger_config import logger
from e2e_tests.objects import (
    ConfigValues,
    E2EAnnotationClass,
    E2EItemLevelProperty,
    TeamConfigValues,
)


def setup_item_level_properties(
    config: ConfigValues, isolated_team: TeamConfigValues
) -> None:
    """
    Setup item-level properties for end to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    """
    logger.debug("Setting up item-level properties")

    item_level_property_types = ["single_select", "multi_select", "text"]
    try:
        for item_level_property_type in item_level_property_types:
            try:
                create_item_level_property(
                    f"test_item_level_property_{item_level_property_type}",
                    item_level_property_type,
                    isolated_team,
                    config,
                )
            except DataAlreadyExists:
                pass
    except E2EException as e:
        print(e)

    except Exception as e:
        print(e)
        pytest.exit("Setup failed - unknown error")


def create_item_level_property(
    name: str,
    item_level_property_type: str,
    isolated_team: TeamConfigValues,
    config: ConfigValues,
) -> E2EItemLevelProperty:
    """
    Creates a single item-level property and returns a corresponding E2EItemLevelProperty

    Parameters
    ----------
    name : str
        The name of the item-level property to create
    item_level_property_type: str
        The type of item-level property to create. Must be `single_select` or `multi_select`
    config : ConfigValues
        The config values to use
    isolated_team: TeamConfigValues
        The isolated team to use

    Returns
    -------
    E2EItemLevelProperty
        The minimum info about the created item-level property
    """
    logger.debug(f"Creating item-level property {name}")
    url = f"{config.server}/api/v2/teams/{isolated_team.team_slug}/properties"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"ApiKey {isolated_team.api_key}",
    }
    payload = {
        "name": name,
        "type": item_level_property_type,
        "granularity": "item",
    }
    if item_level_property_type in ["single_select", "multi_select"]:
        payload["property_values"] = [  # type: ignore
            {"color": "rgba(255,92,0,1.0)", "value": "1"},
            {"color": "rgba(255,92,0,1.0)", "value": "2"},
        ]
    response = requests.post(url, json=payload, headers=headers)
    parsed_response = response.json()
    return E2EItemLevelProperty(
        name=parsed_response["name"],
        dataset_ids=parsed_response["dataset_ids"],
        type=parsed_response["type"],
        id=parsed_response["id"],
    )


def setup_annotation_classes(
    config: ConfigValues, isolated_team: TeamConfigValues
) -> List[E2EAnnotationClass]:
    """
    Setup annotation classes for end to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    List[E2EAnnotationClass]
        The minimum info about the created annotation classes
    """

    annotation_classes: List[E2EAnnotationClass] = []

    logger.info("Setting up annotation classes")
    annotation_class_types = [
        "bounding_box",
        "polygon",
        "ellipse",
        "keypoint",
        "line",
        "mask",
        "skeleton",
        "tag",
    ]
    try:
        for annotation_class_type in annotation_class_types:
            try:
                basic_annotation_class = create_annotation_class(
                    f"test_{annotation_class_type}_basic",
                    annotation_class_type,
                    config,
                    isolated_team,
                    fixed_name=True,
                )
                annotation_classes.append(basic_annotation_class)
            except DataAlreadyExists:
                pass
            try:
                annotation_class_with_subtypes_and_properties = create_annotation_class(
                    f"test_{annotation_class_type}_with_subtypes_and_properties",
                    annotation_class_type,
                    config,
                    isolated_team,
                    fixed_name=True,
                    subtypes=True,
                    properties=True,
                )
                annotation_classes.append(annotation_class_with_subtypes_and_properties)
            except DataAlreadyExists:
                pass
    except E2EException as e:
        print(e)
        pytest.exit("Test run failed while setting up annotation classes")

    except Exception as e:
        print(e)
        pytest.exit("Setup failed - unknown error")

    return annotation_classes


def create_annotation_class(
    name: str,
    annotation_type: str,
    config: ConfigValues,
    isolated_team: TeamConfigValues,
    fixed_name: bool = False,
    subtypes: bool = False,
    properties: bool = False,
) -> E2EAnnotationClass:
    """
    Create a randomised new annotation class, and return its minimal info for reference

    Parameters
    ----------
    name : str
        The name of the annotation class
    annotation_type : str
        The type of the annotation class
    fixed_name : bool
        Whether or not to include a random string in the class name
    subtypes : bool
        Whether or not to enable all possible sub-annotation types for the class
    properties : bool
        Whether ot not to add single & multi-select properties to the class with some values
    Returns
    -------
    E2EAnnotationClass
        The minimal info about the created annotation class
    """
    logger.debug(f"Creating annotation class {name}")
    team_slug = isolated_team.team_slug

    if not fixed_name:
        name = f"{name}_{generate_random_string(4)}_annotation_class"
    host, api_key = config.server, isolated_team.api_key
    url = f"{host}/api/teams/{team_slug}/annotation_classes"
    annotation_types = (
        get_available_annotation_subtypes(annotation_type)
        if subtypes
        else [annotation_type]
    )
    metadata = {"_color": "auto"}
    if annotation_type == "skeleton":
        metadata["skeleton"] = {  # type: ignore
            "edges": [{"from": "2", "to": "node"}],
            "nodes": [
                {"name": "node", "x": 0.5, "y": 0.5},
                {"name": "2", "x": 0.1, "y": 0.1},
            ],
        }
    response = api_call(
        "post",
        url,
        {
            "name": name,
            "annotation_types": annotation_types,
            "metadata": metadata,
        },
        api_key,
    )

    if response.ok:
        annotation_class_info = response.json()
        if properties:
            add_properties_to_class(annotation_class_info, config, isolated_team)
        return E2EAnnotationClass(
            id=annotation_class_info["id"],
            name=annotation_class_info["name"],
            type=annotation_class_info["annotation_types"][0],
        )
    if response.status_code == 422 and "already exists" in response.text:
        raise DataAlreadyExists(
            f"Failed to create annotation class {name} - {response.status_code} - {response.text}"
        )
    raise E2EException(
        f"Failed to create annotation class {name} - {response.status_code} - {response.text}"
    )


def get_available_annotation_subtypes(annotation_type: str) -> List[str]:
    """
    Returns a list of possible subtypes including the main type for a given annotation class type
    """
    annotation_class_subtypes = {
        "bounding_box": [
            "bounding_box",
            "text",
            "attributes",
            "instance_id",
            "directional_vector",
        ],
        "ellipse": ["ellipse", "text", "attributes", "instance_id"],
        "keypoint": ["keypoint", "text", "attributes", "instance_id"],
        "line": ["line", "text", "attributes", "instance_id"],
        "mask": ["mask", "text", "attributes"],
        "polygon": [
            "polygon",
            "text",
            "attributes",
            "instance_id",
            "directional_vector",
        ],
        "skeleton": ["skeleton", "text", "attributes", "instance_id"],
        "tag": ["tag", "text", "attributes"],
    }
    return annotation_class_subtypes[annotation_type]


def add_properties_to_class(
    annotation_class_info: Dict[str, str],
    config: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Adds a single-select & a mulit-select property to the given class, each with two values
    """
    logger.debug(
        f"Adding properties to annotation class {annotation_class_info['name']}"
    )
    url = f"{config.server}/api/v2/teams/{isolated_team.team_slug}/properties"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"ApiKey {isolated_team.api_key}",
    }
    # setup text properties
    for text_granularity in ["annotation", "section"]:
        payload = {
            "name": f"{text_granularity}-text-1",
            "type": "text",
            "required": False,
            "annotation_class_id": annotation_class_info["id"],
            "description": f"Description for a text property on {text_granularity} level",
            "granularity": f"{text_granularity}",
            "property_values": [],
        }
        requests.post(url, json=payload, headers=headers)

    for property_type in ["single_select", "multi_select"]:
        payload = {
            "required": False,
            "type": property_type,
            "name": f"{property_type}-1",
            "property_values": [
                {"type": "string", "value": "1", "color": "auto"},
                {"type": "string", "value": "2", "color": "auto"},
            ],
            "annotation_class_id": annotation_class_info["id"],
        }
        requests.post(url, json=payload, headers=headers)
