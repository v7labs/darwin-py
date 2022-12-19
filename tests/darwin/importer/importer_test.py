from unittest import TestCase


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

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_if_greater_that_total_available_passed(self):
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(900, 768, True)
        self.assertEqual(cpu_limit, 768)

    def test_get_multi_cpu_settings__sets_cpu_count_to_cpu_count_if_greater_that_total_available_passed(self):
        from darwin.importer.importer import _get_multi_cpu_settings as gmcus

        cpu_limit, _ = gmcus(900, 768, True)
        self.assertEqual(cpu_limit, 768)
