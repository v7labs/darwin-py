import re
import uuid

import pytest

from e2e_tests.helpers import run_cli_command
from e2e_tests.objects import E2EDataset


def test_darwin_create_and_delete() -> None:
    uuid_str = str(uuid.uuid4())
    new_dataset_name = "test_dataset_" + uuid_str
    result = run_cli_command(f"darwin dataset create {new_dataset_name}")
    assert result[0] == 0
    assert "has been created" in result[1]
    id_raw = re.search(r"/datasets/(\d+)", result[1])
    assert id_raw is not None
    id = int(id_raw.group(1))

    
    result = run_cli_command(f"yes Y | darwin dataset remove {new_dataset_name}")
    assert result[0] == 0
    
if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])

    