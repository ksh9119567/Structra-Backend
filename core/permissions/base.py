from django.core.exceptions import ObjectDoesNotExist
import logging

from app.organizations.models import OrganizationMembership
from app.teams.models import TeamMembership
from app.projects.models import ProjectMembership

logger = logging.getLogger(__name__)


def _get_role_from_membership(ModelClass, **filters):
    """
    Shared helper: returns the role string for the membership or None.
    Uses select_related to reduce queries if appropriate.
    """
    try:
        membership = ModelClass.objects.get(**filters)
        role = getattr(membership, "role", None)
        logger.debug(f"Role found: {role} for {ModelClass.__name__}")
        return role
    except (ModelClass.DoesNotExist, ObjectDoesNotExist):
        logger.debug(f"Membership not found for {ModelClass.__name__}")
        return None


def get_org_role(user, organization):
    """
    Return role string or None.
    Accepts organization instance or pk.
    """
    if organization is None:
        logger.debug("Organization is None")
        return None
    if user is None or not getattr(user, "is_authenticated", False):
        logger.debug("User is None or not authenticated")
        return None
    try:
        return _get_role_from_membership(OrganizationMembership, user=user, organization=organization)
    except Exception as e:
        logger.error(f"Error getting org role: {str(e)}")
        return None


def get_team_role(user, team):
    if team is None:
        logger.debug("Team is None")
        return None
    if user is None or not getattr(user, "is_authenticated", False):
        logger.debug("User is None or not authenticated")
        return None
    try:
        return _get_role_from_membership(TeamMembership, user=user, team=team)
    except Exception as e:
        logger.error(f"Error getting team role: {str(e)}")
        return None


def get_project_role(user, project):
    if user is None or not getattr(user, "is_authenticated", False):
        logger.debug("User is None or not authenticated")
        return None
    try:
        return _get_role_from_membership(ProjectMembership, user=user, project=project)
    except Exception as e:
        logger.error(f"Error getting project role: {str(e)}")
        return None
