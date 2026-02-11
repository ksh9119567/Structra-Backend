from rest_framework.permissions import BasePermission

from core.permissions.organization import IsOrganizationOwner
from core.permissions.project import IsProjectManager
from core.permissions.team import IsTeamManager

class IsOrgOwnerOrProjectManager(BasePermission):
    message = "Only the organization owner or project manager can perform this action."
    
    def has_object_permission(self, request, view, project):
        org = project.organization

        return bool(
            IsOrganizationOwner().has_object_permission(request, view, org)
            or IsProjectManager().has_object_permission(request, view, project)
        )

class IsOrgOwnerOrTeamManager(BasePermission):
    message = "Only the organization owner or team manager can perform this action."
    
    def has_object_permission(self, request, view, team):
        org = team.organization

        return bool(
            IsOrganizationOwner().has_object_permission(request, view, org)
            or IsTeamManager().has_object_permission(request, view, team)
        )