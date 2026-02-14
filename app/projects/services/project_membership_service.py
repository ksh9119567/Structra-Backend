import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.projects.models import ProjectMembership
from core.utils import get_project_membership

logger = logging.getLogger(__name__)


def add_project_member(*, project, user, role):
    logger.info(f"Adding member {user.email} to project: {project.name} with role: {role}")
    if ProjectMembership.objects.filter(project=project, user=user).exists():
        logger.warning(f"User {user.email} already a member of project: {project.name}")
        raise ValidationError("User already a member")

    membership = ProjectMembership.objects.create(
        project=project,
        user=user,
        role=role
    )
    logger.info(f"Member {user.email} added successfully to project: {project.name}")
    return membership


def remove_project_member(*, project, user):
    logger.info(f"Removing member {user.email} from project: {project.name}")
    if user == project.created_by:
        logger.warning(f"Attempt to remove project creator from project: {project.name}")
        raise PermissionDenied("Cannot remove project creator")

    membership = ProjectMembership.objects.get(
        project=project,
        user=user
    )
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from project: {project.name}")


def self_remove_project_member(*, project, user):
    logger.info(f"Self-remove requested by {user.email} from project: {project.name}")
    if not project.is_self_remove_allowed:
        logger.warning(f"Self-remove not allowed for project: {project.name}")
        raise PermissionDenied("Self removal not allowed")

    if user == project.created_by:
        logger.warning(f"Project creator attempted self-remove from project: {project.name}")
        raise PermissionDenied("Project creator cannot remove themselves")

    membership = get_project_membership(project=project, user=user)
    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from project: {project.name}")


def update_project_member_role(*, project, user, role):
    logger.info(f"Updating role for {user.email} in project: {project.name} to {role}")
    membership = ProjectMembership.objects.get(
        project=project,
        user=user
    )
    membership.role = role
    membership.save(update_fields=["role"])
    logger.info(f"Role updated successfully for {user.email} in project: {project.name}")
    return membership
