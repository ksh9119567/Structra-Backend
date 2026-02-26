import logging

from rest_framework.exceptions import ValidationError

from app.accounts.models import User
from app.organizations.services.organization_membership_service import add_org_member
from app.teams.services.team_membership_service import add_team_member
from app.projects.services.project_membership_service import add_project_member

from .org_utils import get_org
from .team_utils import get_team
from .project_utils import get_project

logger = logging.getLogger(__name__)


def get_user(identifier, kind="email"):
    """
    Returns a user instance by email or phone number.
    """
    logger.debug(f"Getting user by {kind}: {identifier}")
    if identifier:
        try:
            if kind == "email":
                user = User.objects.filter(email__iexact=identifier, is_deleted=False).first()
            elif kind == "phone":
                user = User.objects.filter(phone_no=identifier, is_deleted=False).first()
            if user:
                logger.debug(f"User found: {user.id}")
            else:
                logger.warning(f"User not found for {kind}: {identifier}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by {kind}: {identifier}, error: {str(e)}")
            raise ValidationError("User not found")
    logger.warning("User ID is required but not provided")
    raise ValidationError("User ID is required")
  
  
def add_member(payload):
    """
    Adds a member to the specified organization or team or project.
    """
    try:
        entity_id = payload.get('entity_id')
        user_id = payload.get('user_id')
        role = payload.get('role')
        invite_type = payload.get('invite_type')
        
        user = User.objects.get(id=user_id, is_deleted=False)
        
        if invite_type == 'organization':
            org = get_org(entity_id)
            org_membership = add_org_member(organization=org, user=user, role=role)
            return org_membership
        
        elif invite_type == 'team':
            team = get_team(entity_id)
            team_membership = add_team_member(team=team, user=user, role=role)
            return team_membership
        
        elif invite_type == 'project':
            project = get_project(entity_id)
            project_membership = add_project_member(project=project, user=user, role=role)
            return project_membership

        else:
            raise ValidationError("Invalid invite type")
    
    except Exception as e:
        raise Exception(e)