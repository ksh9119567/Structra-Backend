from rest_framework.exceptions import ValidationError
from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email
from organizations.models import OrganizationMembership


def send_organization_invite(*, organization, user, invited_by, role):
    if OrganizationMembership.objects.filter(
        organization=organization, user=user
    ).exists():
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

    return invite_token
