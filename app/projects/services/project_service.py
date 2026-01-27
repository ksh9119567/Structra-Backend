from rest_framework.exceptions import PermissionDenied, ValidationError

from projects.models import ProjectMembership
from app.organizations.models import OrganizationMembership


def transfer_project_ownership(*, project, new_owner, performed_by):
    """
    Transfer project ownership to another user
    """

    if project.created_by != performed_by:
        raise PermissionDenied("Only project creator can transfer ownership")

    if new_owner == project.created_by:
        raise ValidationError("User is already project creator")

    if not OrganizationMembership.objects.filter(
        organization=project.organization,
        user=new_owner
    ).exists():
        raise ValidationError("User is not a member of the organization")

    if not ProjectMembership.objects.filter(
        project=project,
        user=new_owner
    ).exists():
        raise ValidationError("User is not a member of the project")

    new_owner_membership = ProjectMembership.objects.get(
        project=project,
        user=new_owner
    )
    new_owner_membership.role = "MANAGER"
    new_owner_membership.save(update_fields=["role"])

    project.created_by = new_owner
    project.save(update_fields=["created_by"])


def delete_project(*, project, performed_by):
    if project.created_by != performed_by:
        raise PermissionDenied("Only project creator can delete project")

    project.delete()
