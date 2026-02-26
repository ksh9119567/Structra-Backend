import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.projects.models import ProjectMembership

from core.utils.project_utils import get_project_membership
from core.permissions.base import get_project_role
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY

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


def remove_project_member(*, project, user, performed_by):
    logger.info(f"Removing member {user.email} from project: {project.name}")
    if user == project.created_by:
        logger.warning(f"Attempt to remove project creator from project: {project.name}")
        raise PermissionDenied("Cannot remove project creator")

    target_user_role = get_project_role(user, project)
    action_user_role = get_project_role(performed_by, project)
    
    if PROJECT_ROLE_HIERARCHY[target_user_role] >= PROJECT_ROLE_HIERARCHY[action_user_role]:
        logger.warning(f"Attempt to remove user with equal or higher role from project: {project.name}")
        raise PermissionDenied("Cannot remove user with equal or higher role")
    
    if target_user_role == "MANAGER":
        manager_count = project.membership.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Last manager attempted self-remove from project: {project.name}")
            raise PermissionDenied("Last manager cannot remove themselves.")
    
    membership = ProjectMembership.objects.get(
        project=project,
        user=user
    )
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from project: {project.name}")


def self_remove_project_member(*, project, user):
    logger.info(f"Self-remove requested by {user.email} from project: {project.name}")
    user_role = get_project_role(user, project)
    
    if not project.settings.allow_self_remove:
        logger.warning(f"Self-remove not allowed for project: {project.name}")
        raise PermissionDenied("Self removal not allowed")

    if user == project.created_by:
        logger.warning(f"Project owner attempted self-remove from project: {project.name}")
        raise PermissionDenied("Project owner cannot remove themselves. Must transfer ownership first.")

    if user_role == "MANAGER":
        manager_count = project.membership.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Last manager attempted self-remove from project: {project.name}")
            raise PermissionDenied("Last manager cannot remove themselves.")
        
    membership = get_project_membership(project=project, user=user)
    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from project: {project.name}")


def update_project_member_role(*, project, user, role):
    logger.info(f"Updating role for {user.email} in project: {project.name} to {role}")
    try:
        membership = ProjectMembership.objects.get(
            project=project,
            user=user
        )
        membership.role = role
        membership.save(update_fields=["role"])
        logger.info(f"Role updated successfully for {user.email} in project: {project.name}")
        return membership
    
    except ProjectMembership.DoesNotExist:
        logger.error(f"Membership not found for user {user.email} in project: {project.name}")
        raise ValidationError("Membership not found")
    except Exception as e:
        logger.error(f"Error updating role for user {user.email} in project: {project.name} - {str(e)}")
        raise ValidationError("Error updating role")