import logging

from rest_framework.exceptions import ValidationError

from app.teams.models import TeamMembership
from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email

logger = logging.getLogger(__name__)


def send_team_invite(*, team, user, invited_by, role):
    logger.info(f"Sending team invite to {user.email} for team: {team.name}")
    if TeamMembership.objects.filter(team=team, user=user).exists():
        logger.warning(f"User {user.email} already a member of team: {team.name}")
        raise ValidationError("User already a member")

    invite_token = store_invite_token(
        user.id,
        invite_type="team"
    )

    send_invite_email(
        email=user.email,
        invite_type="Team",
        name=team.name,
        sender=invited_by.email
    )

    logger.info(f"Team invite sent successfully to {user.email}")
    return invite_token
