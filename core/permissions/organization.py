from rest_framework.permissions import BasePermission

from core.constants import ORG_ROLE_HIERARCHY
from core.permissions.base import get_org_role
from core.permissions.mixins import RoleCheckerMixin


class IsOrganizationMember(BasePermission, RoleCheckerMixin):
    message = "You must be a member of this organization."

    def has_object_permission(self, request, view, organization):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_org_role(request.user, organization)
        return role is not None


class IsOrganizationAdmin(BasePermission, RoleCheckerMixin):
    message = "You must be an admin of this organization."

    def has_object_permission(self, request, view, organization):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_org_role(request.user, organization)
        return self.has_minimum_role(role, "ADMIN", ORG_ROLE_HIERARCHY)


class IsOrganizationOwner(BasePermission, RoleCheckerMixin):
    message = "Only the organization owner can perform this action."

    def has_object_permission(self, request, view, organization):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_org_role(request.user, organization)
        return role == "OWNER"
