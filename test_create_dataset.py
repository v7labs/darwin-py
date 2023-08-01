import os
from pathlib import Path

from dotenv import load_dotenv

from e2e_tests.conftest import ConfigValues
from e2e_tests.setup_tests import api_call, create_dataset, create_item


def main() -> None:
    path = Path(__file__).parent / "e2e_tests" / ".env"
    assert path.exists(), f"Path {path} does not exist"

    load_dotenv(path)

    host, key = os.getenv("E2E_ENVIRONMENT"), os.getenv("E2E_API_KEY")

    dataset = create_dataset("test", ConfigValues(api_key=key, server=host))

    print(dataset)


if __name__ == "__main__":
    main()
