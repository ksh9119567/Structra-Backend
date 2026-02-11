from rest_framework.exceptions import ValidationError

from app.projects.models import ProjectMembership
from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email


def send_project_invite(*, project, user, invited_by, role):
    """
    Create invite token and send project invite email
    """

    if ProjectMembership.objects.filter(project=project, user=user).exists():
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

    return invite_token
