import base64
import random
import string
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Literal, Optional

import numpy as np
import pytest
import requests
from PIL import Image

from e2e_tests.exceptions import DataAlreadyExists, E2EException
from e2e_tests.objects import ConfigValues, E2EAnnotationClass, E2EDataset, E2EItem


def api_call(
    verb: Literal["get", "post", "put", "delete"],
    url: str,
    payload: Optional[dict],
    api_key: str,
) -> requests.Response:
    """
    Make an API call to the server
    (Written independently of the client library to avoid relying on tested items)

    Parameters
    ----------
    verb : Literal["get", "post", "put" "delete"]
        The HTTP verb to use
    url : str
        The URL to call
    payload : dict
        The payload to send
    api_key : str
        The API key to use

    Returns
    -------
    requests.Response
        The response object
    """
    headers = {"Authorization": f"ApiKey {api_key}"}
    action = getattr(requests, verb)
    if payload:
        response = action(url, headers=headers, json=payload)
    else:
        response = action(url, headers=headers)
    return response


def generate_random_string(
    length: int = 6, alphabet: str = (string.ascii_lowercase + string.digits)
) -> str:
    """
    A random-enough to avoid collision on test runs prefix generator

    Parameters
    ----------
    length : int
        The length of the prefix to generate

    Returns
    -------
    str
        The generated prefix, of length (length).  Matches [a-z0-9]
    """
    return "".join(random.choice(alphabet) for i in range(length))


def create_dataset(prefix: str, config: ConfigValues) -> E2EDataset:
    """
    Create a randomised new dataset, and return its minimal info for reference

    Parameters
    ----------
    prefix : str
        The prefix to use for the dataset name
    config : ConfigValues
        The config values to use

    Returns
    -------
    E2EDataset
        The minimal info about the created dataset
    """
    name = f"test_dataset_{prefix}_{generate_random_string(4)}"
    host, api_key = config.server, config.api_key
    url = f"{host}/api/datasets"

    if not url.startswith("http"):
        raise E2EException(
            f"Invalid server URL {host} - need to specify protocol in var E2E_ENVIRONMENT"
        )

    try:
        response = api_call("post", url, {"name": name}, api_key)

        if response.ok:
            dataset_info = response.json()
            return E2EDataset(
                # fmt: off
                id=dataset_info["id"],
                name=dataset_info["name"],
                slug=dataset_info["slug"],
                # fmt: on
            )

        raise E2EException(
            f"Failed to create dataset {name} - {response.status_code} - {response.text}"
        )
    except Exception as e:
        print(f"Failed to create dataset {name} - {e}")
        pytest.exit("Test run failed in test setup stage")


def create_annotation_class(
    name: str, annotation_type: str, config: ConfigValues, fixed_name: bool = False,

) -> E2EAnnotationClass:
    """
    Create a randomised new annotation class, and return its minimal info for reference

    Parameters
    ----------
    name : str
        The name of the annotation class
    annotation_type : str
        The type of the annotation class

    Returns
    -------
    E2EAnnotationClass
        The minimal info about the created annotation class
    """
    team_slug = config.team_slug
    
    if not fixed_name:
        name = f"{name}_{generate_random_string(4)}_annotation_class"
    host, api_key = config.server, config.api_key
    url = f"{host}/api/teams/{team_slug}/annotation_classes"
    response = api_call(
        "post",
        url,
        {
            "name": name,
            "annotation_types": [annotation_type],
            "metadata": {"_color": "auto"}
        },
        api_key,
    )

    if response.ok:
        annotation_class_info = response.json()
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


def delete_annotation_class(id: str, config: ConfigValues) -> None:
    """
    Delete an annotation class on the server

    Parameters
    ----------
    id : str
        The id of the annotation class to delete
    config : ConfigValues
        The config values to use
    """
    host, api_key = config.server, config.api_key
    url = f"{host}/api/annotation_classes/{id}"
    try:
        response = api_call(
            "delete",
            url,
            None,
            api_key,
        )
        if not response.ok:
            raise E2EException(
                f"Failed to delete annotation class {id} - {response.status_code} - {response.text}"
            )
    except Exception as e:
        print(f"Failed to delete annotation class {id} - {e}")
        pytest.exit("Test run failed in test setup stage")

def create_item(
    dataset_slug: str, prefix: str, image: Path, config: ConfigValues
) -> E2EItem:
    """
    Creates a randomised new item, and return its minimal info for reference

    Parameters
    ----------
    prefix : str
        The prefix to use for the item name
    config : ConfigValues
        The config values to use

    Returns
    -------
    E2EItem
        The minimal info about the created item
    """
    team_slug = config.team_slug
    name = f"{prefix}_{generate_random_string(4)}_item"
    host, api_key = config.server, config.api_key
    url = f"{host}/api/v2/teams/{team_slug}/items/direct_upload"

    try:
        base64_image = base64.b64encode(image.read_bytes()).decode("utf-8")
        response = api_call(
            "post",
            url,
            {
                "dataset_slug": dataset_slug,
                "items": [
                    {
                        "as_frames": False,
                        "extract_views": False,
                        "file_content": base64_image,
                        "fps": "native",
                        "metadata": {},
                        "name": f"some-item_{generate_random_string(4)}",
                        "path": "/",
                        "tags": ["tag"],
                        "type": "image",
                    }
                ],
                "options": {"force_tiling": False, "ignore_dicom_layout": False},
            },
            api_key,
        )

        if response.ok:
            item_info = response.json()

            if "items" not in response.json() or len(response.json()["items"]) != 1:
                raise E2EException(
                    f"Failed to create item {name} - {response.status_code} - {response.text}:: Received unexpected response from server"
                )

            item_info = response.json()["items"][0]

            return E2EItem(
                name=item_info["name"],
                id=item_info["id"],
                path=item_info["path"],
                file_name=item_info["slots"][0]["file_name"],
                slot_name=item_info["slots"][0]["slot_name"],
                annotations=[],
            )

        raise E2EException(
            f"Failed to create item {name} - {response.status_code} - {response.text}"
        )

    except E2EException as e:
        print(f"Failed to create item {name} - {e}")
        pytest.exit("Test run failed in test setup stage")

    except Exception as e:
        print(f"Failed to create item {name} - {e}")
        pytest.exit("Test run failed in test setup stage")


def create_random_image(
    prefix: str,
    directory: Path,
    height: int = 100,
    width: int = 100,
    fixed_name: bool = False,
) -> Path:
    """
    Create a random image file in the given directory

    Parameters
    ----------

    directory : Path
        The directory to create the image in

    Returns
    -------
    Path
        The path to the created image
    """
    if fixed_name:
        image_name = f"image_{prefix}.png"
    else:
        image_name = f"{prefix}_{generate_random_string(4)}_image.png"

    image_array = np.array(np.random.rand(height, width, 3) * 255)
    im = Image.fromarray(image_array.astype("uint8")).convert("RGBA")
    im.save(str(directory / image_name))

    return directory / image_name


def setup_datasets(config: ConfigValues) -> List[E2EDataset]:
    """
    Setup data for End to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    List[E2EDataset]
        The minimal info about the created datasets
    """
    with TemporaryDirectory() as temp_directory:
        number_of_datasets = 3
        number_of_items = 3

        datasets: List[E2EDataset] = []

        print("Setting up data")

        try:
            prefix = generate_random_string()
            print(f"Using prefix {prefix}")

            for _ in range(number_of_datasets):
                dataset = create_dataset(prefix, config)

                for _ in range(number_of_items):
                    image_for_item = create_random_image(prefix, Path(temp_directory))
                    item = create_item(dataset.name, prefix, image_for_item, config)

                    dataset.add_item(item)

                datasets.append(dataset)

        except E2EException as e:
            print(e)
            pytest.exit("Test run failed in test setup stage")

        except Exception as e:
            print(e)
            pytest.exit("Setup failed - unknown error")

        return datasets


def setup_annotation_classes(config: ConfigValues) -> List[E2EAnnotationClass]:
    """
    Setup data for End to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    List[E2EAnnotationClass]
        The minimal info about the created annotation classes
    """

    annotation_classes: List[E2EAnnotationClass] = []

    print("Setting up annotation classes")
    set_types = [("bb", "bounding_box"), ("poly", "polygon"), ("ellipse", "ellipse")]
    try:
        for annotation_type, annotation_type_name in set_types:
            try:
                annotation_class = create_annotation_class(
                    f"test_{annotation_type}", annotation_type_name, config, fixed_name=True
                )
                annotation_classes.append(annotation_class)
            except DataAlreadyExists:
                pass
    except E2EException as e:
        print(e)
        pytest.exit("Test run failed in test setup stage")

    except Exception as e:
        print(e)
        pytest.exit("Setup failed - unknown error")

    return annotation_classes

def teardown_tests(config: ConfigValues, datasets: List[E2EDataset]) -> None:
    """
    Teardown data for End to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    datasets : List[E2EDataset]
        The minimal info about the created datasets
    """
    failures = []
    print("\nTearing down datasets")
    failures.extend(delete_known_datasets(config, datasets))

    print("Tearing down workflows")
    failures.extend(delete_workflows(config))
    
    print("Tearing down general datasets")
    failures.extend(delete_general_datasets(config))
    
    if failures:
        for item in failures:
            print(item)
        pytest.exit("Test run failed in test teardown stage")

    if failures:
        for item in failures:
            print(item)
        pytest.exit("Test run failed in test teardown stage")

    print("Tearing down data complete")


def delete_workflows(config: ConfigValues) -> List:
    """
    Delete all workflows for the team

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    """
    host, api_key, team_slug = config.server, config.api_key, config.team_slug

    failures = []
    url = f"{host}/api/v2/teams/{team_slug}/workflows"
    response = api_call("get", url, {}, api_key)
    if response.ok:
        items = response.json()
        for item in items:
            if not item["dataset"]:
                continue
            if not item["dataset"]["name"].startswith("test_dataset_"):
                continue
            new_item = {"name": item["name"], "stages": item["stages"]}
            for stage in new_item["stages"]:
                if stage["type"] == "dataset":
                    stage["config"]["dataset_id"] = None
            url = f"{host}/api/v2/teams/{team_slug}/workflows/{item['id']}"
            response = api_call("put", url, new_item, api_key)
            if not response.ok:
                failures.append(
                    f"Failed to delete workflow {item['name']} - {response.status_code} - {response.text}"
                )

            # Now Delete the workflow once dataset is disconnected
            response = api_call("delete", url, None, api_key)
            if not response.ok:
                failures.append(
                    f"Failed to delete workflow {item['name']} - {response.status_code} - {response.text}"
                )
    return failures

def delete_known_datasets(config: ConfigValues, datasets: List[E2EDataset]) -> List:
    """
    Delete all known datasets for the team

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    """
    host, api_key, _ = config.server, config.api_key, config.team_slug

    failures = []
    for dataset in datasets:
        url = f"{host}/api/datasets/{dataset.id}/archive"
        response = api_call("put", url, {}, api_key)

        if not response.ok:
            failures.append(
                f"Failed to delete dataset {dataset.name} - {response.status_code} - {response.text}"
            )
    return failures

def delete_general_datasets(config: ConfigValues) -> List:
    host, api_key, _ = config.server, config.api_key, config.team_slug
    # teardown any other datasets of specific format
    url = f"{host}/api/datasets"
    failures = []
    response = api_call("get", url, {}, api_key)
    if response.ok:
        items = response.json()
        for item in items:
            if not item["name"].startswith("test_dataset_"):
                continue
            url = f"{host}/api/datasets/{item['id']}/archive"
            response = api_call("put", url, None, api_key)
            if not response.ok:
                failures.append(
                    f"Failed to delete dataset {item['name']} - {response.status_code} - {response.text}"
                )
    return failures

def teardown_annotation_classes(config: ConfigValues, annotation_classes: List[E2EAnnotationClass]) -> None:
    for annotation_class in annotation_classes:
        delete_annotation_class(str(annotation_class.id), config)
    team_slug = config.team_slug
    host = config.server
    response = api_call("get", f"{host}/api/teams/{team_slug}/annotation_classes", None, config.api_key)
    all_annotations = response.json()['annotation_classes']
    for annotation_class in all_annotations:
        if annotation_class['name'].startswith('test_'):
            delete_annotation_class(annotation_class['id'], config)