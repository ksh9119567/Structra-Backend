import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import NotFound, ValidationError

from app.teams.models import Team, TeamMembership

logger = logging.getLogger(__name__)


def get_team(team_id):
    """
    Returns a team instance by team_id.
    Raises NotFound (404) for a missing, soft-deleted or malformed id.
    """
    logger.debug(f"Getting team: {team_id}")
    if not team_id:
        logger.warning("Team ID is required but not provided")
        raise ValidationError("Team ID is required")

    try:
        obj = Team.objects.filter(id=team_id, is_deleted=False).first()
    except (DjangoValidationError, ValueError):
        obj = None  # malformed UUID
    if not obj:
        logger.warning(f"Team not found: {team_id}")
        raise NotFound("Team not found")
    logger.debug(f"Team found: {obj.name}")
    return obj

def get_all_team_memberships(team_id):
    """
    Returns all members of a team by team_id.
    """
    if team_id:
        return TeamMembership.objects.filter(team_id=team_id)
    raise ValidationError("Team ID is required")

def get_team_membership(team_id, user):
    """
    Returns a membership instance by team_id and user.
    """
    if team_id and user:
        try:
            return TeamMembership.objects.get(team_id=team_id, user=user)
        except TeamMembership.DoesNotExist:
            raise NotFound("Team membership not found")
    raise ValidationError("Team ID and user are required")
