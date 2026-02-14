import logging

from rest_framework.exceptions import ValidationError

from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email
from app.organizations.models import OrganizationMembership

logger = logging.getLogger(__name__)


def send_organization_invite(*, organization, user, invited_by, role):
    logger.info(f"Sending organization invite to {user.email} for org: {organization.name}")
    if OrganizationMembership.objects.filter(
        organization=organization, user=user
    ).exists():
        logger.warning(f"User {user.email} already a member of org: {organization.name}")
        raise ValidationError("User already a member")

    invite_token = store_invite_token(
        user.id,
        invite_type="organization"
    )

    send_invite_email(
        email=user.email,
        invite_type="Organization",
        name=organization.name,
        sender=invited_by.email
    )

    logger.info(f"Organization invite sent successfully to {user.email}")
    return invite_token
