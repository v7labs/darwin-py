import sys
from os.path import dirname
from pathlib import Path

import orjson as json
import pytest
import xml.etree.ElementTree as ET

from e2e_tests.helpers import assert_cli, run_cli_command


class TestExportCli:
    this_file_path = Path(dirname(__file__)).absolute()
    data_path = (this_file_path / ".." / "data" / "convert").resolve()

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
                with file.open("rb") as f:
                    content = f.read()

                with Path(expected_path / file.name).open("rb") as f:
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
        [
            ("yolo_segmented", data_path / "yolov8/from", data_path / "yolov8/to"),
            ("yolo", data_path / "yolo/from", data_path / "yolo/to"),
            ("cvat", data_path / "cvat/from", data_path / "cvat/to"),
            ("pascalvoc", data_path / "pascalvoc/from", data_path / "pascalvoc/to"),
            (
                "nifti",
                data_path / "nifti-legacy-scaling/from",
                data_path / "nifti-legacy-scaling/to",
            ),
            (
                "nifti",
                data_path / "nifti-no-legacy-scaling/from",
                data_path / "nifti-no-legacy-scaling/to",
            ),
            (
                "nifti",
                data_path / "nifti-multislot/from",
                data_path / "nifti-multislot/to",
            ),
            (
                "instance_mask",
                data_path / "instance_mask/from",
                data_path / "instance_mask/to",
            ),
            pytest.param(
                "coco",
                data_path / "coco/from",
                data_path / "coco/to",
                marks=pytest.mark.skipif(
                    sys.platform == "win32",
                    reason="File paths are different on Windows, leading to test failure",
                ),
            ),
            (
                "semantic_mask",
                data_path / "semantic_mask/from",
                data_path / "semantic_mask/to",
            ),
        ],
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
        self.patch_format(format, tmp_path)
        assert_cli(result, 0)
        self.compare_directories(expectation_path, tmp_path)

    def patch_format(self, format: str, path: Path) -> None:
        """
        Patch files based on format to match the expected output.
        """
        patch_methods = {
            "coco": self.patch_coco,
            "cvat": self.patch_cvat,
        }
        patch_method = patch_methods.get(format)
        if patch_method:
            patch_method(path)

    def patch_coco(self, path: Path) -> None:
        """
        Patch coco file to match the expected output, includes changes to year and date_created,
        wrapped in try except so that format errors are still caught later with correct error messages
        """
        try:
            with open(path / "output.json", "r") as f:
                contents = f.read()
                temp = json.loads(contents)
                temp["info"]["year"] = 2023
                temp["info"]["date_created"] = "2023/12/05"
            with open(path / "output.json", "w") as f:
                op = json.dumps(
                    temp, option=json.OPT_INDENT_2 | json.OPT_SERIALIZE_NUMPY
                ).decode("utf-8")
                f.write(op)
        except Exception:
            print(f"Error patching {path}")

    def patch_cvat(self, path: Path) -> None:
        """
        Patch cvat file to match the expected output.
        """
        try:
            tree = ET.parse(path / "output.xml")
            root = tree.getroot()
            # Adjust the required fields
            dumped_elem = root.find(".//meta/dumped")
            if dumped_elem is not None:
                dumped_elem.text = "2024-10-25 10:33:01.789498+00:00"
            created_elem = root.find(".//meta/task/created")
            if created_elem is not None:
                created_elem.text = "2024-10-25 10:33:01.789603+00:00"
            updated_elem = root.find(".//meta/task/updated")
            if updated_elem is not None:
                updated_elem.text = "2024-10-25 10:33:01.789608+00:00"
            tree.write(path / "output.xml")
        except ET.ParseError:
            print(f"Error parsing XML in {path}")
        except Exception as e:
            print(f"Error patching {path}: {e}")


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
