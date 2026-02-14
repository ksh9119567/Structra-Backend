import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.organizations.models import OrganizationMembership

logger = logging.getLogger(__name__)


def add_member(*, organization, user, role):
    logger.info(f"Adding member {user.email} to organization: {organization.name} with role: {role}")
    if OrganizationMembership.objects.filter(
        organization=organization, user=user
    ).exists():
        logger.warning(f"User {user.email} already a member of organization: {organization.name}")
        raise ValidationError("User already a member")

    membership = OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=role
    )
    logger.info(f"Member {user.email} added successfully to organization: {organization.name}")
    return membership


def remove_member(*, organization, user):
    logger.info(f"Removing member {user.email} from organization: {organization.name}")
    if user == organization.owner:
        logger.warning(f"Attempt to remove owner from organization: {organization.name}")
        raise PermissionDenied("Cannot remove owner")

    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from organization: {organization.name}")


def self_remove(*, organization, user):
    logger.info(f"Self-remove requested by {user.email} from organization: {organization.name}")
    if not organization.is_self_remove_allowed:
        logger.warning(f"Self-remove not allowed for organization: {organization.name}")
        raise PermissionDenied("Self remove not allowed")

    if user == organization.owner:
        logger.warning(f"Owner attempted self-remove from organization: {organization.name}")
        raise PermissionDenied("Owner cannot remove self")

    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from organization: {organization.name}")


def update_role(*, organization, user, role):
    logger.info(f"Updating role for {user.email} in organization: {organization.name} to {role}")
    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.role = role
    membership.save()
    logger.info(f"Role updated successfully for {user.email} in organization: {organization.name}")
    return membership
