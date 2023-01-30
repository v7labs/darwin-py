from pathlib import Path
from typing import Optional
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rich.console import Console

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

    def test_get_multi_cpu_settings__disables_multiprocessing_if_either_core_count_or_core_limit_is_one(self) -> None:
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        res_1 = gmcus(None, 1, True)
        res_2 = gmcus(1, 16, True)
        self.assertEqual(res_1, (1, False))
        self.assertEqual(res_2, (1, False))

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_minus_two_if_omitted(self) -> None:
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(None, 768, True)
        self.assertEqual(cpu_limit, 766)

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_if_greater_that_total_available_passed(self) -> None:
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(900, 768, True)
        self.assertEqual(cpu_limit, 768)


class Test_get_files_for_parsing(TestCaseImporter):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_get_files_for_parsing_dir_handling(self) -> None:
        with patch.object(Path, "is_dir") as mock_is_dir:
            with patch.object(Path, "glob") as mock_glob:
                mock_is_dir.return_value = True
                mock_glob.return_value = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]
                result = _get_files_for_parsing([Path("example_dir")])
                assert result == [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]

    def test_get_files_for_parsing_single_file(self) -> None:
        with patch.object(Path, "is_dir") as mock_is_dir:
            with patch.object(Path, "glob") as mock_glob:
                mock_is_dir.return_value = False

                result = _get_files_for_parsing([Path("example_dir")])
                assert result == [Path("example_dir")]
                mock_glob.assert_not_called()


class Test_find_and_parse(TestCaseImporter):
    mock_console: Optional[MagicMock]

    def setUp(self) -> None:
        self.mock_console = MagicMock(spec=Console)
        return super().setUp()

    def tearDown(self) -> None:
        self.mock_console = None
        return super().tearDown()

    @patch("darwin.importer.importer._get_multi_cpu_settings")
    @patch("darwin.importer.importer._get_files_for_parsing")
    @patch("darwin.importer.importer.WorkerPool")
    def test_uses_mpire_if_use_multi_cpu_true(
        self, mock_wp: MagicMock, mock_gffp: MagicMock, mock_gmcus: MagicMock
    ) -> None:

        from darwin.importer.importer import find_and_parse

        mock_gmcus.return_value = (2, True)
        mock_gffp.return_value = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]

        mock_importer = MagicMock()
        mock_map = MagicMock()

        class MockWorkerPool:
            def __init__(self) -> None:
                self.map = mock_map

            def __enter__(self) -> "MockWorkerPool":
                return self

            def __exit__(self, *args) -> None:  # type: ignore
                pass

        mock_wp.return_value = MockWorkerPool()
        mock_map.return_value = ["1", "2"]

        result = find_and_parse(mock_importer, [Path("example_dir")], self.mock_console, True, 2)

        mock_wp.assert_called_once()
        mock_wp.assert_called_with(2)
        mock_map.assert_called_once()

        self.assertEqual(result, ["1", "2"])

    @patch("darwin.importer.importer._get_files_for_parsing")
    @patch("darwin.importer.importer.WorkerPool")
    def test_runs_single_threaded_if_use_multi_cpu_false(self, mock_wp: MagicMock, mock_gffp: MagicMock) -> None:

        from darwin.importer.importer import find_and_parse

        mock_gffp.return_value = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]

        mock_importer = MagicMock()
        mock_importer.side_effect = ["1", "2"]

        result = find_and_parse(mock_importer, [Path("example_dir")], self.mock_console, False)

        mock_wp.assert_not_called()
        mock_importer.assert_called()

        self.assertEqual(result, ["1", "2"])

    @patch("darwin.importer.importer._get_multi_cpu_settings")
    @patch("darwin.importer.importer._get_files_for_parsing")
    @patch("darwin.importer.importer.WorkerPool")
    def test_returns_list_if_solo_value(self, mock_wp: MagicMock, mock_gffp: MagicMock, mock_gmcus: MagicMock) -> None:

        from darwin.importer.importer import find_and_parse

        mock_gmcus.return_value = (2, True)
        mock_gffp.return_value = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]

        mock_importer = MagicMock()
        mock_map = MagicMock()

        class MockWorkerPool:
            def __init__(self) -> None:
                self.map = mock_map

            def __enter__(self) -> "MockWorkerPool":
                return self

            def __exit__(self, *args) -> None:  # type: ignore
                pass

        mock_wp.return_value = MockWorkerPool()
        mock_map.return_value = "1"

        result = find_and_parse(mock_importer, [Path("example_dir")], self.mock_console, True, 2)

        mock_wp.assert_called_once()
        mock_wp.assert_called_with(2)
        mock_map.assert_called_once()

        self.assertEqual(result, ["1"])

    @patch("darwin.importer.importer._get_multi_cpu_settings")
    @patch("darwin.importer.importer._get_files_for_parsing")
    @patch("darwin.importer.importer.WorkerPool")
    def test_returns_none_if_pool_raises_error(
        self, mock_wp: MagicMock, mock_gffp: MagicMock, mock_gmcus: MagicMock
    ) -> None:

        from darwin.importer.importer import find_and_parse

        mock_gmcus.return_value = (2, True)
        mock_gffp.return_value = [Path("example_dir/file1.txt"), Path("example_dir/file2.txt")]

        mock_importer = MagicMock()
        mock_map = MagicMock()

        class MockWorkerPool:
            def __init__(self) -> None:
                self.map = mock_map

            def __enter__(self) -> "MockWorkerPool":
                return self

            def __exit__(self, *args) -> None:  # type: ignore
                pass

        mock_wp.return_value = MockWorkerPool()
        mock_map.side_effect = Exception("Test")

        result = find_and_parse(mock_importer, [Path("example_dir")], self.mock_console, True, 2)

        mock_wp.assert_called_once()
        mock_wp.assert_called_with(2)
        mock_map.assert_called_once()

        self.assertEqual(result, None)
