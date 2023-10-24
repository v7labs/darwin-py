from typing import Generator
from unittest.mock import Mock, patch

from pytest import fixture, raises
from responses import RequestsMock

from darwin.future.core.client import ClientCore, DarwinConfig
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.data_objects.team import TeamMemberCore
from darwin.future.meta.client import Client
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.meta.objects.team import Team
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.meta.objects.fixtures import *


@fixture
def _delete_by_slug_mock() -> Generator:
    with patch.object(Team, "_delete_dataset_by_slug") as mock:
        yield mock


@fixture
def _delete_by_id_mock() -> Generator:
    with patch.object(Team, "_delete_dataset_by_id") as mock:
        yield mock


def test_team_meta_collects_members(
    base_meta_team: Team,
    base_client: ClientCore,
    base_team_member: TeamMemberCore,
    base_team_member_json: dict,
) -> None:
    with RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(rsps.GET, endpoint, json=[base_team_member_json])
        members = base_meta_team.members._collect()
        assert len(members) == 1
        assert members[0]._element == base_team_member


# `delete_dataset` tests
def test_delete_dataset_returns_exceptions_thrown(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    _delete_by_slug_mock.side_effect = Exception("test exception")

    valid_client = Client(base_config)
    with raises(Exception):
        _ = Team.delete_dataset(valid_client, "test_dataset")

    assert _delete_by_slug_mock.call_count == 1
    assert _delete_by_id_mock.call_count == 0


def test_delete_dataset_calls_delete_by_slug_as_appropriate(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    valid_client = Client(base_config)

    _ = Team.delete_dataset(valid_client, "test_dataset")

    assert _delete_by_slug_mock.call_count == 1
    assert _delete_by_id_mock.call_count == 0


def test_delete_dataset_calls_delete_by_id_as_appropriate(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    valid_client = Client(base_config)

    _ = Team.delete_dataset(valid_client, 1)

    assert _delete_by_slug_mock.call_count == 0
    assert _delete_by_id_mock.call_count == 1


def test_delete_by_slug__returns_dataset_deleted_if_dataset_found(
    base_config: DarwinConfig,
) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_url + "?id=test_dataset",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        rsps.add(
            rsps.PUT,
            base_url + "/1/archive",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        dataset_deleted = Team._delete_dataset_by_slug(valid_client, valid_slug)

        assert dataset_deleted == 1


def test_delete_by_id_returns_dataset_deleted_if_dataset_found(
    base_config: DarwinConfig,
) -> None:
    valid_client = Client(base_config)
    valid_id = 1

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.PUT,
            base_url + "/1/archive",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        dataset_deleted = Team._delete_dataset_by_id(valid_client, valid_id)

        assert dataset_deleted == 1


# Test `_delete_by_id`
def test_delete_by_id_raises_exception_if_not_passed_int_and_client(
    base_config: DarwinConfig,
) -> None:
    valid_client = Client(base_config)
    valid_id = 1
    invalid_client = "client"
    invalid_id = "1"

    with raises(AssertionError):
        Team._delete_dataset_by_id(valid_client, invalid_id)  # type: ignore

    with raises(AssertionError):
        Team._delete_dataset_by_id(invalid_client, valid_id)  # type: ignore


# Test `_delete_by_slug`
def test_delete_by_slug_raises_exception_if_not_passed_str_and_client(
    base_config: DarwinConfig,
) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"
    invalid_client = "client"
    invalid_slug = 1

    with raises(AssertionError):
        Team._delete_dataset_by_slug(valid_client, invalid_slug)  # type: ignore

    with raises(AssertionError):
        Team._delete_dataset_by_slug(invalid_client, valid_slug)  # type: ignore


def test_create_dataset(base_meta_team: Team, base_config: DarwinConfig) -> None:
    base_url = base_config.base_url + "api/datasets"
    valid_slug = "test_dataset"
    valid_name = "test dataset"
    with RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            base_url,
            json={"id": 1, "name": valid_name, "slug": valid_slug},
            status=201,
        )

        dataset_created = base_meta_team.create_dataset(valid_slug)
        assert dataset_created is not None
        assert isinstance(dataset_created, Dataset)
        assert isinstance(dataset_created._element, DatasetCore)
        assert dataset_created.id == 1
        assert dataset_created.name == valid_name
        assert dataset_created.slug == valid_slug


def test_team_str_method(base_meta_team: Team) -> None:
    assert (
        str(base_meta_team)
        == "Team\n\
- Team Name: test-team\n\
- Team Slug: test-team\n\
- Team ID: 0\n\
- 0 member(s)"
    )


def test_team_repr_method(base_meta_team: Team) -> None:
    assert repr(base_meta_team) == str(base_meta_team)
