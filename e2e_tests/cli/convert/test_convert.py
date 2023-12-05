from os.path import dirname
from pathlib import Path
from typing import Tuple

import pytest

from e2e_tests.helpers import assert_cli, run_cli_command


class TestExportCli:
    this_file_path = Path(dirname(__file__)).absolute()
    data_path = (this_file_path / ".." / ".." / "data").resolve()

    @pytest.fixture(autouse=True)
    def config(self) -> None:
        assert self.data_path.exists(), "Data path does not exist, tests cannot run"

    def compare_directories(self, path: Path, expected_path: Path) -> None:
        """
        Compare two directories recursively
        """
        assert path.exists() and expected_path.exists()
        assert path.is_dir() and expected_path.is_dir()

        for file in path.iterdir():
            if file.is_dir():
                # Recursively compare directories
                self.compare_directories(file, expected_path / file.name)
            else:
                if file.name.startswith("."):
                    # Ignore hidden files
                    continue

                # Compare files
                with file.open("r") as f:
                    content = f.read()

                with Path(expected_path / file.name).open() as f:
                    expected_content = f.read()

                if content != expected_content:
                    print(f"Expected file: {expected_path / file.name}")
                    print(f"Expected Content: \n{expected_content}")
                    print("---------------------")
                    print(f"Actual file: {file}")
                    print(f"Actual Content: \n{content}")
                    assert False, f"File {file} does not match expected file"


    @pytest.mark.parametrize(
        "format, input_path, expectation_path",
        [("yolo_segmented", data_path / "yolov8/from", data_path / "yolov8/to"),
         ("coco", data_path / "coco/from", data_path / "coco/to")],
    )
    def test_darwin_convert(
        self, format: str, input_path: Path, expectation_path: Path, tmp_path: Path
    ) -> None:
        """
        Test converting a file format to another format
        """
        assert (
            input_path is not None and expectation_path is not None
        ), "Input or expectation path is None"
        assert (
            input_path.exists() and expectation_path.exists()
        ), f"Input path {input_path.absolute()} or expectation path {expectation_path.absolute()} does not exist"
        assert (
            input_path.is_dir() and expectation_path.is_dir()
        ), f"Input path {input_path.absolute()} or expectation path {expectation_path.absolute()} is not a directory"

        result = run_cli_command(
            f"darwin convert {format} {str(input_path)} {str(tmp_path)}"
        )

        assert_cli(result, 0)
        self.compare_directories(expectation_path, tmp_path)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
