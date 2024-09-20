from subprocess import run
from time import sleep
from typing import Optional, Dict, Any, Tuple, List

from attr import dataclass

from darwin.exceptions import DarwinException

import json
import re
import tempfile
import uuid
from typing import Generator
import pytest
import requests
import time
from e2e_tests.objects import E2EDataset, ConfigValues


@dataclass
class CLIResult:
    """Wrapper for the result of a CLI command after decoding the stdout and stderr."""

    return_code: int
    stdout: str
    stderr: str


SERVER_WAIT_TIME = 10


def run_cli_command(
    command: str,
    working_directory: Optional[str] = None,
    yes: bool = False,
    server_wait: int = SERVER_WAIT_TIME,
) -> CLIResult:
    """
    Run a CLI command and return the return code, stdout, and stderr.

    Parameters
    ----------
    command : str
        The command to run.
    working_directory : str, optional
        The working directory to run the command in.

    Returns
    -------
    Tuple[int, str, str]
        The return code, stdout, and stderr.
    """

    # Do not allow directory traversal
    if ".." in command or (working_directory and ".." in working_directory):
        raise DarwinException("Cannot pass directory traversal to 'run_cli_command'.")

    if yes:
        command = f"yes Y | {command}"

    if working_directory:
        result = run(
            command,
            cwd=working_directory,
            capture_output=True,
            shell=True,
        )
    else:
        result = run(
            command,
            capture_output=True,
            shell=True,
        )
    sleep(server_wait)  # wait for server to catch up
    try:
        return CLIResult(
            result.returncode,
            result.stdout.decode("utf-8"),
            result.stderr.decode("utf-8"),
        )
    except UnicodeDecodeError:
        return CLIResult(
            result.returncode,
            result.stdout.decode("cp437"),
            result.stderr.decode("cp437"),
        )


def format_cli_output(result: CLIResult) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n"


def assert_cli(
    result: CLIResult,
    expected_return_code: int = 0,
    in_stdout: Optional[str] = None,
    in_stderr: Optional[str] = None,
    expected_stdout: Optional[str] = None,
    expected_stderr: Optional[str] = None,
    inverse: bool = False,
) -> None:
    assert result.return_code == expected_return_code, format_cli_output(result)
    if not inverse:
        if in_stdout:
            assert in_stdout in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout == expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr == expected_stderr, format_cli_output(result)
    else:
        if in_stdout:
            assert in_stdout not in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr not in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout != expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr != expected_stderr, format_cli_output(result)


def list_items(api_key, dataset_id, team_slug, base_url):
    """
    List items in Darwin dataset, handling pagination.
    """
    url = f"{base_url}/api/v2/teams/{team_slug}/items?dataset_ids={dataset_id}"
    headers = {"accept": "application/json", "Authorization": f"ApiKey {api_key}"}
    items = []

    while url:
        response = requests.get(url, headers=headers)
        if response.ok:
            data = json.loads(response.text)
            items.extend(data["items"])
            next_page = data.get("page", {}).get("next")
            if next_page:
                url = f"{base_url}/{team_slug}/items?dataset_ids={dataset_id}&page[from]={next_page}"
            else:
                url = None
        else:
            raise requests.exceptions.HTTPError(
                f"GET request failed with status code {response.status_code}."
            )

    return items


def wait_until_items_processed(
    config_values: ConfigValues, dataset_id: int, timeout: int = 600
):
    """
    Waits until all items in a dataset have finished processing before attempting to upload annotations.
    Raises a `TimeoutError` if the process takes longer than the specified timeout.
    """
    sleep_duration = 10
    api_key = config_values.api_key
    team_slug = config_values.team_slug
    base_url = config_values.server
    elapsed_time = 0

    while elapsed_time < timeout:
        items = list_items(api_key, dataset_id, team_slug, base_url)
        if not items:
            return
        if all(item["processing_status"] != "processing" for item in items):
            break
        print(f"Waiting {sleep_duration} seconds for items to finish processing...")
        time.sleep(sleep_duration)
        elapsed_time += sleep_duration

    if elapsed_time >= timeout:
        raise TimeoutError(
            f"Processing items took longer than the specified timeout of {timeout} seconds."
        )


def normalize_expected_annotation(
    annotation: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns a single read-in Darwin JSON 2.0 annotation into a structure for comparison
    with other annotations, rounding coordinates to the 3rd decimal place where applicable.

    This is necessary because the `/annotations` endpoint only records coordinates to the
    3rd decimal place. If we don't round to 3dp, assertions comparing annotations will fail

    If sub-annotations or properties are present, these are also returned
    """

    def round_coordinates(data: Any) -> Any:
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = round_coordinates(value)
        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = round_coordinates(data[i])
        elif isinstance(data, (int, float)):
            data = round(data, 3)
        return data

    # Check for subtypes
    subtypes = {}
    if "instance_id" in annotation:
        subtypes["instance_id"] = annotation["instance_id"]
    if "text" in annotation:
        subtypes["text"] = annotation["text"]
    if "attributes" in annotation:
        subtypes["attributes"] = annotation["attributes"]
    if "directional_vector" in annotation:
        subtypes["directional_vector"] = round_coordinates(
            annotation["directional_vector"]
        )

    # Check for properties
    annotation_properties = []
    if "properties" in annotation:
        annotation_properties = sorted(
            annotation["properties"], key=lambda x: (x["name"], x["value"])
        )

    # Check for main type
    if "polygon" in annotation:
        annotation = {
            "polygon": {"paths": round_coordinates(annotation["polygon"]["paths"])}
        }
    if "bounding_box" in annotation:
        annotation = {"bounding_box": round_coordinates(annotation["bounding_box"])}
    if "ellipse" in annotation:
        annotation = {"ellipse": round_coordinates(annotation["ellipse"])}
    if "keypoint" in annotation:
        annotation = {"keypoint": round_coordinates(annotation["keypoint"])}
    if "skeleton" in annotation:
        annotation = {"skeleton": round_coordinates(annotation["skeleton"])}
    if "line" in annotation:
        annotation = {"line": round_coordinates(annotation["line"])}
    if "tag" in annotation:
        annotation = {"tag": annotation["tag"]}
    if "mask" in annotation:
        annotation = {"mask": annotation["mask"]}
    if "raster_layer" in annotation:
        annotation = {
            "dense_rle": annotation["raster_layer"]["dense_rle"],
            "total_pixels": annotation["raster_layer"]["total_pixels"],
        }
    return annotation, subtypes, annotation_properties


def normalize_actual_annotation(
    annotation: Dict[str, Any], properties: Dict[str, List]
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Converts a single annotation into a structure for comparison with other annotations,
    rounding coordinates to the 3rd decimal place where applicable.

    This is necessary because the `/annotations` endpoint only records coordinates to the
    3rd decimal place. If we don't round to 3dp, assertions comparing annotations will fail

    If sub-annotations or properties are present, these are also returned
    """

    def round_coordinates(data: Any) -> Any:
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = round_coordinates(value)
        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = round_coordinates(data[i])
        elif isinstance(data, (int, float)):
            data = round(data, 3)
        return data

    annotation_data = annotation["data"]

    # Check for subtypes
    subtypes = {}
    if "instance_id" in annotation_data:
        subtypes["instance_id"] = annotation_data["instance_id"]
    if "text" in annotation_data:
        subtypes["text"] = annotation_data["text"]
    if "attributes" in annotation_data:
        subtypes["attributes"] = annotation_data["attributes"]
    if "directional_vector" in annotation_data:
        subtypes["directional_vector"] = round_coordinates(
            annotation_data["directional_vector"]
        )

    # Check for properties
    annotation_properties = []
    if "properties" in annotation:
        for frame_index, props in annotation["properties"].items():
            for property_id, property_value_ids in props.items():
                team_prop = next(
                    (
                        prop
                        for prop in properties["properties"]
                        if property_id == prop["id"]
                    )
                )
                property_name = team_prop["name"]
                for property_value_id in property_value_ids:
                    property_value = next(
                        prop_val["value"]
                        for prop_val in team_prop["property_values"]
                        if property_value_id == prop_val["id"]
                    )
                    annotation_properties.append(
                        {
                            "frame_index": int(frame_index),
                            "name": property_name,
                            "value": property_value,
                        }
                    )

    if "polygon" in annotation_data:
        # The `/annotations` endpoint reports polygon paths in `path`
        # This must be converted to `paths` for consistency with exports
        if "path" in annotation_data["polygon"]:
            annotation_data = {
                "polygon": {
                    "paths": round_coordinates([annotation_data["polygon"]["path"]])
                }
            }
        annotation_data = {
            "polygon": {"paths": round_coordinates(annotation_data["polygon"]["paths"])}
        }
    if "bounding_box" in annotation_data:
        annotation_data = {
            "bounding_box": round_coordinates(annotation_data["bounding_box"])
        }
    if "ellipse" in annotation_data:
        annotation_data = {"ellipse": round_coordinates(annotation_data["ellipse"])}
    if "keypoint" in annotation_data:
        annotation_data = {"keypoint": round_coordinates(annotation_data["keypoint"])}
    if "skeleton" in annotation_data:
        annotation_data = {"skeleton": round_coordinates(annotation_data["skeleton"])}
    if "line" in annotation_data:
        annotation_data = {"line": round_coordinates(annotation_data["line"])}
    if "tag" in annotation_data:
        annotation_data = {"tag": annotation_data["tag"]}
    if "mask" in annotation_data:
        annotation_data = {"mask": annotation_data["mask"]}
    if "raster_layer" in annotation_data:
        annotation_data = {
            "dense_rle": annotation_data["raster_layer"]["dense_rle"],
            "total_pixels": annotation_data["raster_layer"]["total_pixels"],
        }
    return (
        annotation_data,
        subtypes,
        sorted(annotation_properties, key=lambda x: (x["name"], x["value"])),
    )


@pytest.fixture
def new_dataset() -> E2EDataset:
    """Create a new dataset via darwin cli and return the dataset object, complete with teardown"""
    uuid_str = str(uuid.uuid4())
    new_dataset_name = "test_dataset_" + uuid_str
    result = run_cli_command(f"darwin dataset create {new_dataset_name}")
    assert_cli(result, 0)
    id_raw = re.findall(r"datasets[/\\+](\d+)", result.stdout)
    assert id_raw is not None and len(id_raw) == 1
    id = int(id_raw[0])
    teardown_dataset = E2EDataset(id, new_dataset_name, None)
    pytest.datasets.append(teardown_dataset)  # type: ignore
    return teardown_dataset


@pytest.fixture
def local_dataset(new_dataset: E2EDataset) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset
