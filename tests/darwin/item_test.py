import darwin


def test_remote_path_gets_rid_of_initial_root_character_if_its_there():
    dataset_item = darwin.item.DatasetItem(
        id=1,
        filename="filename.jpg",
        status="new",
        archived=False,
        filesize=0,
        dataset_id=1,
        dataset_slug="test-dataset",
        seq=1,
        current_workflow_id=None,
        path="/long/remote/path",
    )
    assert dataset_item.remote_path == "long/remote/path"


def test_remote_path_is_equal_to_path_otherwise():
    dataset_item = darwin.item.DatasetItem(
        id=1,
        filename="filename.jpg",
        status="new",
        archived=False,
        filesize=0,
        dataset_id=1,
        dataset_slug="test-dataset",
        seq=1,
        current_workflow_id=None,
        path="long/remote/path",
    )
    assert dataset_item.remote_path == "long/remote/path"


def test_full_path_uses_remote_path():
    dataset_item = darwin.item.DatasetItem(
        id=1,
        filename="filename.jpg",
        status="new",
        archived=False,
        filesize=0,
        dataset_id=1,
        dataset_slug="test-dataset",
        seq=1,
        current_workflow_id=None,
        path="/long/remote/path",
    )
    assert dataset_item.full_path == "long/remote/path/filename.jpg"
