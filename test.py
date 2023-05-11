from darwin.future.core.client import Client, DarwinConfig
from darwin.future.meta.queries.team_member import TeamMemberQuery

client = Client.local()

members = TeamMemberQuery().collect(client)
print(len(members))
