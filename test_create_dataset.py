import os
from pathlib import Path

from dotenv import load_dotenv

from e2e_tests.conftest import ConfigValues
from e2e_tests.setup_tests import (
    create_annotation,
    create_dataset,
    create_item,
    create_random_image,
    setup_tests,
    teardown_tests,
)

# TODO List:
# 1. Dogfood creating dataset ✔︎
# 2. Dogfood creating item ✔️
# 3. Dogfood creating annotation ~
# 4. Dogfood teardown


def main() -> None:
    path = Path(__file__).parent / "e2e_tests" / ".env"
    assert path.exists(), f"Path {path} does not exist"

    load_dotenv(path)

    host, key, team = os.getenv("E2E_ENVIRONMENT"), os.getenv("E2E_API_KEY"), os.getenv("E2E_TEAM")

    if not host or not key or not team:
        raise ValueError(f"Environment variables not set: {host}, {key}, {team}")

    config_values = ConfigValues(api_key=key, server=host, team_slug=team)

    output = setup_tests(config_values)

    print(output)

    # dataset = create_dataset("test", config_values)

    # image = create_random_image("test", Path(__file__).parent)

    # item = create_item(dataset.slug, "test", image, config_values)

    # annotation = create_annotation(dataset.slug, item, 1, config_values)

    # print(dataset)
    # print(item)
    # print(annotation)

    # teardown_tests(config_values, [dataset])


if __name__ == "__main__":
    main()
