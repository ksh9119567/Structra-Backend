from rest_framework.exceptions import ValidationError, PermissionDenied

from projects.models import ProjectMembership
from core.utils import get_project_membership


def add_project_member(*, project, user, role):
    if ProjectMembership.objects.filter(project=project, user=user).exists():
        raise ValidationError("User already a member")

    return ProjectMembership.objects.create(
        project=project,
        user=user,
        role=role
    )


def remove_project_member(*, project, user):
    if user == project.created_by:
        raise PermissionDenied("Cannot remove project creator")

    membership = ProjectMembership.objects.get(
        project=project,
        user=user
    )
    membership.delete()


def self_remove_project_member(*, project, user):
    if not project.is_self_remove_allowed:
        raise PermissionDenied("Self removal not allowed")

    if user == project.created_by:
        raise PermissionDenied("Project creator cannot remove themselves")

    membership = get_project_membership(project=project, user=user)
    membership.delete()


def update_project_member_role(*, project, user, role):
    membership = ProjectMembership.objects.get(
        project=project,
        user=user
    )
    membership.role = role
    membership.save(update_fields=["role"])
    return membership
