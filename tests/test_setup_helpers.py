import re
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
from PIL import Image

from e2e_tests.conftest import ConfigValues
from e2e_tests.setup_tests import (
    E2EDataset,
    add_classes_to_team,
    api_call,
    create_dataset,
    create_item,
    create_random_image,
    generate_random_string,
)
from tests.server_example_returns import (
    ADD_CLASSES_RETURN_RAW,
    CREATE_DATASET_RETURN_RAW,
    CREATE_ITEM_RETURN_RAW,
)


@pytest.fixture
def config_values() -> ConfigValues:
    return ConfigValues(
        # fmt: off
        api_key="test_api_key", 
        server="https://test_server",
        team_slug="test_team"
        # fmt: on
    )


@responses.activate
def test_api_call() -> None:
    responses.add(
        responses.GET,
        "http://0.0.0.0/testurl",
        status=218,
    )

    api_call("get", "http://0.0.0.0/testurl", {"key": "json"}, "test_api_key")

    assert len(responses.calls) == 1
    req_call: responses.Call = responses.calls[0]  # type: ignore

    assert req_call.request.url == "http://0.0.0.0/testurl"
    assert req_call.request.headers["Authorization"] == "ApiKey test_api_key"
    assert req_call.request.body == b'{"key": "json"}'


def test_generate_random_string() -> None:
    for i in range(1, 1000):
        assert len(op := generate_random_string(i)) == i
        assert op.isalnum()


@pytest.mark.xfail("Not implemented")
def test_add_classes_to_team(config_values: ConfigValues) -> None:
    with patch("e2e_tests.setup_tests.api_call") as mock_api_call:
        mock_api_call.return_value.ok = True
        mock_api_call.return_value.status_code = 200
        mock_api_call.return_value.json.return_value = ADD_CLASSES_RETURN_RAW

        bbox_class, polygon_class = add_classes_to_team(
            "test-prefix",
            # fmt: off
            E2EDataset(
                1,
                "test_dataset",
                "test_dataset",
            ),
            # fmt: on
            config_values,
        )

    if not bbox_class or not polygon_class:
        pytest.fail("Classes were not created")
    else:
        assert bbox_class.name == "test_bbox_class"
        assert bbox_class.id == 13371337
        assert bbox_class.slug == "test_bbox_class"

        assert polygon_class.name == "test_polygon_class"
        assert polygon_class.id == 13371337
        assert polygon_class.slug == "test_polygon_class"


def test_create_dataset(config_values: ConfigValues) -> None:
    with patch("e2e_tests.setup_tests.api_call") as mock_api_call:
        mock_api_call.return_value.ok = True
        mock_api_call.return_value.status_code = 200
        mock_api_call.return_value.text = "test_text"
        mock_api_call.return_value.json.return_value = CREATE_DATASET_RETURN_RAW

        dataset = create_dataset("test-prefix", config_values)

    if not dataset:
        pytest.fail("Dataset was not created")
    else:
        assert dataset.name == "test_dataset"
        assert dataset.id == 13371337
        assert dataset.slug == "test_dataset"


def test_create_item(tmpdir: Path, config_values: ConfigValues) -> None:
    with patch("e2e_tests.setup_tests.api_call") as mock_api_call:
        mock_api_call.return_value.ok = True
        mock_api_call.return_value.status_code = 200
        mock_api_call.return_value.text = "test_text"
        mock_api_call.return_value.json.return_value = CREATE_ITEM_RETURN_RAW

        image_path = create_random_image("test_prefix", Path(tmpdir))

        item = create_item(
            # fmt: off
            "test_dataset", 
            "test_prefix", 
            image_path, 
            config_values
            # fmt: on
        )

    if not item:
        pytest.fail("Item was not created")
    else:
        assert item.name == "test_dataset"
        assert item.path == "test_path"
        assert item.id == "test_id"
        assert item.file_name == "slot_file_name"
        assert item.slot_name == "slot_name"


def test_create_random_image(tmpdir: Path) -> None:
    image_location = create_random_image("prefix", Path(tmpdir))
    assert image_location.exists()
    assert image_location.is_file()
    FILENAME_MATCHER = re.compile(r"^prefix\_[A-z0-9]+\.png$")
    assert FILENAME_MATCHER.match(image_location.name)
    assert Image.open(image_location).size == (10, 10)

    image_2 = create_random_image("prefix", Path(tmpdir), 5, 9)
    assert image_2.exists()
    assert Image.open(image_2).size == (9, 5)


@pytest.mark.xfail("Not implemented")
def test_setup() -> None:
    pytest.fail("Not implemented")


@pytest.mark.xfail("Not implemented")
def test_teardown() -> None:
    pytest.fail("Not implemented")


if __name__ == "__main__":
    pytest.main()
