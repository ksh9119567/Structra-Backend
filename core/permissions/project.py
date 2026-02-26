from rest_framework.permissions import BasePermission

from core.constants.project_constant import PROJECT_ROLE_HIERARCHY
from core.permissions.base import get_project_role
from core.permissions.mixins import RoleCheckerMixin


class IsProjectMember(BasePermission):
    message = "You must be a member of this project."

    def has_object_permission(self, request, view, project):
        if not getattr(request.user, "is_authenticated", False):
            return False
        return get_project_role(request.user, project) is not None


class IsProjectContributor(BasePermission, RoleCheckerMixin):
    message = "Only contributors can perform this action."

    def has_object_permission(self, request, view, project):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_project_role(request.user, project)
        return self.has_minimum_role(role, "CONTRIBUTOR", PROJECT_ROLE_HIERARCHY)


class IsProjectManager(BasePermission, RoleCheckerMixin):
    message = "Only project managers can perform this action."

    def has_object_permission(self, request, view, project):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_project_role(request.user, project)
        return self.has_minimum_role(role, "MANAGER", PROJECT_ROLE_HIERARCHY)
    

class IsProjectOwner(BasePermission, RoleCheckerMixin):
    message = "Only project owners can perform this action."

    def has_object_permission(self, request, view, project):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = get_project_role(request.user, project)
        return self.has_minimum_role(role, "OWNER", PROJECT_ROLE_HIERARCHY)
