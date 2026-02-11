from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from app.accounts.models import User
from app.organizations.models import Organization, OrganizationMembership
from app.teams.models import Team, TeamMembership


def get_user(identifier, kind="email"):
    """
    Returns a user instance by email or phone number.
    """
    if kind == "email":
        return User.objects.filter(email__iexact=identifier).first()
    elif kind == "phone":
        return User.objects.filter(phone_no=identifier).first()
    return None

def get_org(org_id):
    """
    Returns a organization instance by org_id.
    """
    if org_id:
        try:
            obj = Organization.objects.filter(id=org_id).first()
            if not obj:
                raise NotFound("Organization not found")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID is required")

def get_org_membership(org_id, user):
    """
    Returns a membership instance by org_id and user.
    """
    if org_id and user:
        try:
            obj = OrganizationMembership.objects.get(organization_id=org_id, user=user)
            if not obj:
                raise NotFound("Organization not found")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID and user are required")

def get_all_org_memberships(org_id):
    """
    Returns all members of an organization by org_id.
    """
    if org_id:
        try:
            return OrganizationMembership.objects.filter(organization_id=org_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID is required")

def get_team(team_id):
    """
    Returns a team instance by team_id.
    """
    if team_id:
        try:
            obj = Team.objects.filter(id=team_id).first()
            if not obj:
                raise NotFound("Team not found")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID is required")

def get_all_team_memberships(team_id):
    """
    Returns all members of a team by team_id.
    """
    if team_id:
        try:
            return TeamMembership.objects.filter(team_id=team_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID is required")

def get_team_membership(team_id, user):
    """
    Returns a membership instance by team_id and user.
    """
    if team_id and user:
        try:
            obj = TeamMembership.objects.get(team_id=team_id, user=user)
            if not obj:
                raise ValidationError("User is not a member of this team")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID and user are required")