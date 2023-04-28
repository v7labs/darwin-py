from enum import Enum


class TeamMemberRole(Enum):
    TEAM_OWNER = "owner"
    TEAM_ADMIN = "admin"
    USER = "member"
    WORKFORCE_MANAGER = "workforce_manager"
    WORKER = "annotator"
