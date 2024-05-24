from typing import Optional, Union

from darwin.future.core.client import ClientCore
from darwin.future.core.datasets import get_dataset, remove_dataset
from darwin.future.core.team.get_team import get_team
from darwin.future.data_objects.team import TeamCore
from darwin.future.exceptions import MissingDataset
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.meta.queries.dataset import DatasetQuery
from darwin.future.meta.queries.item import ItemQuery
from darwin.future.meta.queries.team_member import TeamMemberQuery
from darwin.future.meta.queries.workflow import WorkflowQuery


class Team(MetaBase[TeamCore]):
    """
    Team Meta object. Facilitates the creation of Query objects, lazy loading of sub
    fields like members unlike other MetaBase objects, does not extend the __next__
    function because it is not iterable. This is because Team is linked to api key and
    only one team can be returned, but stores a list of teams for consistency. This
    does mean however that to access the underlying team object, you must access the
    first element of the list
    team = client.team[0]

    Args:
        MetaBase (Team): Generic MetaBase object expanded by Team core object return
            type

    Returns:
        Team: Team object

    Attributes:
        name (str): The name of the team.
        slug (str): The slug of the team.
        id (int): The id of the team.
        members (TeamMemberQuery): A query of team members associated with the team.
        datasets (DatasetQuery): A query of datasets associated with the team.
        workflows (WorkflowQuery): A query of workflows associated with the team.

    Methods:
        create_dataset(slug: str) -> Dataset:
            Creates a new dataset with the given name and slug.
        delete_dataset(client: Client, id: int) -> None:
            Removes the dataset with the given slug.


    Example Usage:
        # Get the team object
        client = Client.local()
        team = client.team[0]

        # Get a dataset object associated with the team
        dataset = team.datasets.where(name="my_dataset_name").collect_one()

        # Create a new dataset associated with the team
        new_dataset = team.create_dataset(name="new_dataset", slug="new_dataset_slug")

        # Remove a dataset associated with the team
        team.remove_dataset(slug="my_dataset_slug")

        # Get a workflow object associated with the team
        workflow = team.workflows.where(name="my_workflow_name").collect_one()

        # Get a team member object associated with the team
        team_member = team.members.where(email="...")
    """

    def __init__(self, client: ClientCore, team: Optional[TeamCore] = None) -> None:
        team = team or get_team(client)
        super().__init__(client=client, element=team)

    @property
    def name(self) -> str:
        return self._element.name

    @property
    def id(self) -> int:
        assert self._element.id is not None
        return self._element.id

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client, meta_params={"team_slug": self.slug})

    @property
    def slug(self) -> str:
        return self._element.slug

    @property
    def datasets(self) -> DatasetQuery:
        return DatasetQuery(self.client, meta_params={"team_slug": self.slug})

    @property
    def workflows(self) -> WorkflowQuery:
        return WorkflowQuery(self.client, meta_params={"team_slug": self.slug})

    @property
    def items(self) -> ItemQuery:
        return ItemQuery(
            self.client, meta_params={"team_slug": self.slug, "dataset_ids": "all"}
        )

    @classmethod
    def delete_dataset(cls, client: ClientCore, dataset_id: Union[int, str]) -> int:
        """
        Deletes a dataset by id or slug

        Parameters
        ----------
        dataset_id: Union[int, str]
            The id or slug of the dataset to delete

        Returns
        -------
        Tuple[Optional[List[Exception]], int]
            A tuple containing a list of exceptions and the number of datasets deleted
        """
        if isinstance(dataset_id, str):
            dataset_deleted = cls._delete_dataset_by_slug(client, dataset_id)
        else:
            dataset_deleted = cls._delete_dataset_by_id(client, dataset_id)

        return dataset_deleted

    @staticmethod
    def _delete_dataset_by_slug(client: ClientCore, slug: str) -> int:
        """
        (internal) Deletes a dataset by slug

        Parameters
        ----------
        client: MetaClient
            The client to use to make the request

        slug: str
            The slug of the dataset to delete

        Returns
        -------
        int
            The dataset deleted
        """
        assert_is(isinstance(client, ClientCore), "client must be a Core Client")
        assert_is(isinstance(slug, str), "slug must be a string")

        dataset = get_dataset(client, slug)
        if dataset and dataset.id:
            dataset_deleted = remove_dataset(client, dataset.id)
        else:
            raise MissingDataset(f"Dataset with slug {slug} not found")

        return dataset_deleted

    @staticmethod
    def _delete_dataset_by_id(client: ClientCore, dataset_id: int) -> int:
        """
        (internal) Deletes a dataset by id

        Parameters
        ----------
        client: Client
            The client to use to make the request

        dataset_id: int
            The id of the dataset to delete

        Returns
        -------
        int
            The dataset deleted
        """
        assert_is(isinstance(client, ClientCore), "client must be a Client")
        assert_is(isinstance(dataset_id, int), "dataset_id must be an integer")

        dataset_deleted = remove_dataset(client, dataset_id)
        return dataset_deleted

    def create_dataset(self, slug: str) -> Dataset:
        core = Dataset.create_dataset(self.client, slug)
        return Dataset(
            client=self.client, element=core, meta_params={"team_slug": self.slug}
        )

    def __str__(self) -> str:
        return f"Team\n\
- Team Name: {self._element.name}\n\
- Team Slug: {self._element.slug}\n\
- Team ID: {self._element.id}\n\
- {len(self._element.members if self._element.members else [])} member(s)"
