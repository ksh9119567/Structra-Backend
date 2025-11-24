from django.core.exceptions import ObjectDoesNotExist

from app.organizations.models import OrganizationMembership
from app.teams.models import TeamMembership
from app.projects.models import ProjectMembership


def _get_role_from_membership(ModelClass, **filters):
    """
    Shared helper: returns the role string for the membership or None.
    Uses select_related to reduce queries if appropriate.
    """
    try:
        membership = ModelClass.objects.get(**filters)
        return getattr(membership, "role", None)
    except (ModelClass.DoesNotExist, ObjectDoesNotExist):
        return None


def get_org_role(user, organization):
    """
    Return role string or None.
    Accepts organization instance or pk.
    """
    if organization is None:
        return None
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return _get_role_from_membership(OrganizationMembership, user=user, organization=organization)
    except Exception:
        return None


def get_team_role(user, team):
    if team is None:
        return None
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return _get_role_from_membership(TeamMembership, user=user, team=team)
    except Exception:
        return None


def get_project_role(user, project):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return _get_role_from_membership(ProjectMembership, user=user, project=project)
    except Exception:
        return None
