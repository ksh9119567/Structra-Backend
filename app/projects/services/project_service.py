import logging

from rest_framework.exceptions import PermissionDenied, ValidationError

from app.projects.models import ProjectMembership
from app.organizations.models import OrganizationMembership

logger = logging.getLogger(__name__)


def transfer_project_ownership(*, project, new_owner, performed_by):
    """
    Transfer project ownership to another user
    """
    logger.info(f"Transferring ownership of project: {project.name} to {new_owner.email}")

    if project.created_by != performed_by:
        logger.warning(f"Non-creator {performed_by.email} attempted to transfer ownership of project: {project.name}")
        raise PermissionDenied("Only project creator can transfer ownership")

    if new_owner == project.created_by:
        logger.warning(f"Attempt to transfer ownership to current creator for project: {project.name}")
        raise ValidationError("User is already project creator")

    if not OrganizationMembership.objects.filter(
        organization=project.organization,
        user=new_owner
    ).exists():
        logger.warning(f"User {new_owner.email} not a member of organization for project: {project.name}")
        raise ValidationError("User is not a member of the organization")

    if not ProjectMembership.objects.filter(
        project=project,
        user=new_owner
    ).exists():
        logger.warning(f"User {new_owner.email} not a member of project: {project.name}")
        raise ValidationError("User is not a member of the project")

    new_owner_membership = ProjectMembership.objects.get(
        project=project,
        user=new_owner
    )
    new_owner_membership.role = "MANAGER"
    new_owner_membership.save(update_fields=["role"])

    project.created_by = new_owner
    project.save(update_fields=["created_by"])
    logger.info(f"Ownership transferred successfully to {new_owner.email} for project: {project.name}")


def delete_project(*, project, performed_by):
    logger.info(f"Deleting project: {project.name}")
    if project.created_by != performed_by:
        logger.warning(f"Non-creator {performed_by.email} attempted to delete project: {project.name}")
        raise PermissionDenied("Only project creator can delete project")

    project.delete()
    logger.info(f"Project deleted successfully: {project.name}")
