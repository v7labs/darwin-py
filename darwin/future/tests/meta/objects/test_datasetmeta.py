from responses import RequestsMock

from darwin.future.meta.objects.dataset import DatasetMeta

# `datasets` tests
# TODO datasets tests

# `get_dataset_by_id` tests
# TODO get_dataset_by_id tests

# `create_dataset` tests
# TODO create_dataset tests

# `update_dataset` tests
# TODO update_dataset tests


# `delete_dataset` tests
def test_it_returns_a_dataset_it_has_deleted() -> None:
    with RequestsMock() as rsps:
        rsps.add(
            rsps.DELETE,
            "https://darwin.v7labs.com/api/v1/datasets/1",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        exception, deleted = DatasetMeta.delete_dataset(1)

        assert exception is None
        assert deleted == 1


def test_it_returns_none_if_no_dataset_to_delete() -> None:
    with RequestsMock() as rsps:
        rsps.add(
            rsps.DELETE,
            "https://darwin.v7labs.com/api/v1/datasets/1",
            json={"detail": "Not found."},
            status=404,
        )
        exception, deleted = DatasetMeta.delete_dataset(1)

        assert exception is not None
        assert deleted is None
