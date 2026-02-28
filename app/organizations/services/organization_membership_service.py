import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.organizations.models import OrganizationMembership

from core.permissions.base import get_org_role
from core.constants.org_constant import ORG_ROLE_HIERARCHY

logger = logging.getLogger(__name__)


def add_org_member(*, organization, user, role):
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


def remove_member(*, organization, user, performed_by):
    logger.info(f"Removing member {user.email} from organization: {organization.name}")
    if user == organization.owner:
        logger.warning(f"Attempt to remove owner from organization: {organization.name}")
        raise PermissionDenied("Cannot remove owner")

    target_user_role = get_org_role(user, organization)
    action_user_role = get_org_role(performed_by, organization)
    
    if ORG_ROLE_HIERARCHY[target_user_role] >= ORG_ROLE_HIERARCHY[action_user_role]:
        logger.warning(f"Attempt to remove user with equal or higher role from organization: {organization.name}")
        raise PermissionDenied("Cannot remove user with equal or higher role")

    if target_user_role == "ADMIN":
        admin_count = organization.memberships.filter(role="ADMIN").count()
        if admin_count == 1:
            logger.warning(f"Last admin attempted removal from organization: {organization.name}")
            raise PermissionDenied("Last admin cannot be removed")
    
    membership = OrganizationMembership.objects.get(organization=organization, user=user)
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from organization: {organization.name}")


def self_remove(*, organization, user):
    logger.info(f"Self-remove requested by {user.email} from organization: {organization.name}")
    user_role = get_org_role(user, organization)
    
    if not organization.settings.allow_self_removal:
        logger.warning(f"Self-remove not allowed for organization: {organization.name}")
        raise PermissionDenied("Self remove not allowed")

    if user == organization.owner:
        logger.warning(f"Owner attempted self-remove from organization: {organization.name}")
        raise PermissionDenied("Owner cannot remove himself. Must transfer ownership first.")

    if user_role == "ADMIN":
        admin_count = organization.memberships.filter(role="ADMIN").count()
        if admin_count == 1:
            logger.warning(f"Last admin attempted self-remove from organization: {organization.name}")
            raise PermissionDenied("Last admin cannot remove himself.")
    
    membership = OrganizationMembership.objects.get(organization=organization, user=user)
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
