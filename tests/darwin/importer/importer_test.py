from unittest import TestCase
from pathlib import Path
from darwin.importer.importer import _get_files_for_parsing


class TestCaseImporter(TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()


class Test_get_multi_cpu_settings(TestCaseImporter):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_get_multi_cpu_settings__disables_multiprocessing_if_either_core_count_or_core_limit_is_one(self):
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        res_1 = gmcus(None, 1, True)
        res_2 = gmcus(1, 16, True)
        self.assertEqual(res_1, (1, False))
        self.assertEqual(res_2, (1, False))

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_minus_two_if_omitted(self):
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(None, 768, True)
        self.assertEqual(cpu_limit, 766)

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_if_greater_that_total_available_passed(self):
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(900, 768, True)
        self.assertEqual(cpu_limit, 768)


class Test_get_files_for_parsing(TestCaseImporter):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_get_files_for_parsing(self):
        # Test directory with multiple files
        dir_path = Path("example_dir")
        dir_files = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt"), Path("example_dir/subdir/file3.txt")]
        for file in dir_files:
            file.touch()
        result = _get_files_for_parsing([dir_path])
        assert set(result) == set(dir_files)

        # Clean up
        for file in dir_files:
            file.unlink()
        dir_path.rmdir()

        # Test single file
        file_path = Path("example.txt")
        file_path.touch()
        result = _get_files_for_parsing([file_path])
        assert result == [file_path]
        file_path.unlink()

        # Test multiple input files
        file1 = Path("file1.txt")
        file1.touch()
        file2 = Path("file2.txt")
        file2.touch()
        result = _get_files_for_parsing([file1, file2])
        assert set(result) == {file1, file2}
        file1.unlink()
        file2.unlink()
