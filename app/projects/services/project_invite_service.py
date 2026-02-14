import logging

from rest_framework.exceptions import ValidationError

from app.projects.models import ProjectMembership
from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email

logger = logging.getLogger(__name__)


def send_project_invite(*, project, user, invited_by, role):
    """
    Create invite token and send project invite email
    """
    logger.info(f"Sending project invite to {user.email} for project: {project.name}")

    if ProjectMembership.objects.filter(project=project, user=user).exists():
        logger.warning(f"User {user.email} already a member of project: {project.name}")
        raise ValidationError("User already a member")

    invite_token = store_invite_token(
        user.id,
        invite_type="project"
    )

    send_invite_email(
        email=user.email,
        invite_type="Project",
        name=project.name,
        sender=invited_by.email
    )

    logger.info(f"Project invite sent successfully to {user.email}")
    return invite_token
