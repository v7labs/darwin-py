from pathlib import Path

import pytest

from e2e_tests.setup import (
    api_call,
    create_dataset,
    create_item,
    create_random_image,
    generate_random_string,
    setup,
    teardown,
)


def test_api_call() -> None:
    ...


def test_generate_random_string() -> None:
    ...


def test_create_dataset() -> None:
    ...


def test_create_item() -> None:
    ...


def test_create_random_image(tmpdir: Path) -> None:
    image_location = create_random_image("prefix", tmpdir)
    assert image_location.exists()


def test_setup() -> None:
    ...


def test_teardown() -> None:
    ...


if __name__ == "__main__":
    pytest.main()
