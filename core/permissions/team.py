from rest_framework.permissions import BasePermission

from core.constants.team_constant import TEAM_ROLE_HIERARCHY
from core.permissions.base import get_team_role
from core.permissions.mixins import RoleCheckerMixin


class IsTeamPart(BasePermission):
    message = "You must be a part of the team to perform this action."

    def has_object_permission(self, request, view, team):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_team_role(request.user, team)
        return role in TEAM_ROLE_HIERARCHY

class IsTeamMember(BasePermission):
    message = "You must be a team member."

    def has_object_permission(self, request, view, team):
        if not getattr(request.user, "is_authenticated", False):
            return False
        return get_team_role(request.user, team) is not None


class IsTeamManager(BasePermission, RoleCheckerMixin):
    message = "Only team managers can perform this action."

    def has_object_permission(self, request, view, team):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_team_role(request.user, team)
        return self.has_minimum_role(role, "MANAGER", TEAM_ROLE_HIERARCHY)
    

class IsTeamOwner(BasePermission, RoleCheckerMixin):
    message = "Only team owners can perform this action."
    
    def has_object_permission(self, request, view, obj):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_team_role(request.user, obj)
        return self.has_minimum_role(role, "OWNER", TEAM_ROLE_HIERARCHY)
