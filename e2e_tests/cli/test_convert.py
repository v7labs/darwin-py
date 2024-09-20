# from pathlib import Path


# from e2e_tests.helpers import assert_cli, run_cli_command
# from e2e_tests.objects import E2EDataset


# TODO
# def test_convert_to_coco(local_dataset: E2EDataset) -> None:
#     """
#     Test converting a pre-defined Darwin JSON 2.0 release to the coco format.
#     """
#     convert_dir = Path(__file__).parent / "data" / "convert" / "to_coco"
#     result = run_cli_command(
#         f"darwin dataset convert {local_dataset.name} coco {convert_dir}"
#     )
#     assert_cli(result, 0)
#     # Add validation logic here

# TODO
# def test_convert_to_cvat(local_dataset: E2EDataset) -> None:
#     """
#     Test converting a pre-defined Darwin JSON 2.0 release to the cvat format.
#     """
#     convert_dir = Path(__file__).parent / "data" / "convert" / "to_cvat"
#     result = run_cli_command(
#         f"darwin dataset convert {local_dataset.name} cvat {convert_dir}"
#     )
#     assert_cli(result, 0)
#     # Add validation logic here


# Add more tests for other convert scenarios as described in the plan
