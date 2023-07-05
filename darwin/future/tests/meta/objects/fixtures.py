from pytest import fixture, raises

from darwin.future.core.client import Client, DarwinConfig
from darwin.future.data_objects.team import Team
from darwin.future.meta.objects.team import TeamMeta


@fixture
def base_meta_team(base_client: Client, base_team: Team) -> TeamMeta:
    return TeamMeta(base_client, [base_team])
