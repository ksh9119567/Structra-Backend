import logging

from rest_framework.exceptions import ValidationError

from app.accounts.models import User
from app.organizations.models import OrganizationMembership
from app.teams.models import TeamMembership
from app.projects.models import ProjectMembership

logger = logging.getLogger(__name__)


def delete_user_account(user):
    try:
        logger.info(f"Deleting user account for user: {user.email}")
        
        # Case 1: If user is already self-deleted, raise error
        if user.is_deleted:
            logger.warning(f"Attempt to delete already deleted account: {user.email}")
            raise ValidationError("User account is already deleted.")
        
        # Case 2: If user is inactive but not deleted, raise error
        if not user.is_active and not user.is_deleted:
            logger.warning(f"Attempt to delete inactive but not deleted account: {user.email}")
            raise ValidationError("User account is inactive and cannot be deleted.")
        
        # Case 3: User is org owner, team owner, or project owner, raise error
        if OrganizationMembership.objects.filter(user=user, role="owner").exists():
            logger.warning(f"Attempt to delete account of organization owner: {user.email}")
            raise ValidationError("Cannot delete account of an organization owner. Please transfer ownership or delete the organization first.")
        
        if TeamMembership.objects.filter(user=user, role='owner').exists():
            logger.warning(f"Attempt to delete account of team owner: {user.email}")
            raise ValidationError("Cannot delete account of a team owner. Please transfer owner role or delete the team first.")
        
        if ProjectMembership.objects.filter(user=user, role='owner').exists():
            logger.warning(f"Attempt to delete account of project owner: {user.email}")
            raise ValidationError("Cannot delete account of a project owner. Please transfer owner role or delete the project first.")

        # Case 4: If user is admin of any org and no other admin exists, raise error
        if OrganizationMembership.objects.filter(user=user, role="admin").exists():
            orgs = OrganizationMembership.objects.filter(user=user, role="admin").values_list("organization_id", flat=True)
            for org_id in orgs:
                if not OrganizationMembership.objects.filter(organization_id=org_id, role="admin").exclude(user=user).exists():
                    logger.warning(f"Attempt to delete account of last organization admin: {user.email}")
                    raise ValidationError("Cannot delete account of an organization admin. Please transfer admin role or delete the organization first.")
                
        # Case 5: If user is last manager of any team or project, raise error
        if TeamMembership.objects.filter(user=user, role='manager').exists():
            teams = TeamMembership.objects.filter(user=user, role="manager").values_list("team_id", flat=True)
            for team_id in teams:
                if not TeamMembership.objects.filter(team_id=team_id, role="manager").exclude(user=user).exists():
                    logger.warning(f"Attempt to delete account of last team manager: {user.email}")
                    raise ValidationError("Cannot delete account of a team manager. Please transfer manager role or delete the team first.")
                
        if ProjectMembership.objects.filter(user=user, role='manager').exists():
            projects = ProjectMembership.objects.filter(user=user, role="manager").values_list("project_id", flat=True)
            for project_id in projects:
                if not ProjectMembership.objects.filter(project_id=project_id, role="manager").exclude(user=user).exists():
                    logger.warning(f"Attempt to delete account of last project manager: {user.email}")
                    raise ValidationError("Cannot delete account of a project manager. Please transfer manager role or delete the project first.")
                
        # Case 6: Soft delete the user account
        user.is_deleted = True
        user.is_active = False
        user.save()
    
    except Exception as e:
        logger.error(f"Error deleting user account for user: {user.email} - {str(e)}")
        raise e