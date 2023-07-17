import pytest

from e2e_tests.conftest import ConfigValues


@pytest.mark.xfail(reason="Fails unless you set the server and key as below")
def test_example_test_does_nothing(config_values: ConfigValues) -> None:
    assert config_values.server == "https://api.example.com"
    assert config_values.api_key == "1234567890"

    assert True


if __name__ == "__main__":
    pytest.main()
