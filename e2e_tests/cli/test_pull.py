# from e2e_tests.helpers import assert_cli, run_cli_command
# from e2e_tests.objects import E2EDataset


# def test_pull_data(local_dataset: E2EDataset) -> None:
#     """
#     Test pulling a dataset release with default arguments.
#     """
#     result = run_cli_command(f"darwin dataset pull {local_dataset.name}")
#     assert_cli(result, 0)
#     # Add validation logic here


# def test_pull_data_flat_structure(local_dataset: E2EDataset) -> None:
#     """
#     Test pulling a dataset release with use_folders set to False.
#     """
#     result = run_cli_command(
#         f"darwin dataset pull {local_dataset.name} --use-folders False"
#     )
#     assert_cli(result, 0)
#     # Add validation logic here
