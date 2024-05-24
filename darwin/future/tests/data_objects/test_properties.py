from pathlib import Path

import pytest

from darwin.future.data_objects.properties import MetaDataClass, SelectedProperty


@pytest.fixture
def path_to_metadata_folder() -> Path:
    return Path("darwin/future/tests/data")


@pytest.fixture
def path_to_metadata(path_to_metadata_folder: Path) -> Path:
    return path_to_metadata_folder / ".v7" / "metadata.json"


def test_properties_metadata_loads_folder(path_to_metadata: Path) -> None:
    metadata = MetaDataClass.from_path(path_to_metadata)
    assert metadata is not None
    assert len(metadata) == 2


def test_properties_metadata_loads_file(path_to_metadata: Path) -> None:
    metadata = MetaDataClass.from_path(path_to_metadata)
    assert metadata is not None
    assert len(metadata) == 2


def test_properties_metadata_fails() -> None:
    path = Path("darwin/future/tests/data/does_not_exist.json")
    with pytest.raises(FileNotFoundError):
        MetaDataClass.from_path(path)

    path = Path("darwin/future/tests/data/does_not_exist")
    with pytest.raises(FileNotFoundError):
        MetaDataClass.from_path(path)


def test_can_parse_unpopulated_required_properties() -> None:
    selected_property = SelectedProperty(
        frame_index=None, name="name", type="type", value=None
    )
    assert selected_property is not None
