from rest_framework.permissions import BasePermission

from core.permissions.organization import IsOrganizationOwner
from core.permissions.project import IsProjectManager

class IsOrgOwnerOrProjectManager(BasePermission):
    def has_object_permission(self, request, view, project):
        org = project.organization

        return bool(
            IsOrganizationOwner().has_object_permission(request, view, org)
            or IsProjectManager().has_object_permission(request, view, project)
        )