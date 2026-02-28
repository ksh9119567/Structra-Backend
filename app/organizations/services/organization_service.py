import logging

from rest_framework.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


def transfer_ownership(*, organization, new_owner, performed_by):
    logger.info(f"Transferring ownership of organization: {organization.name} from {performed_by.email} to {new_owner.email}")
    if organization.owner != performed_by:
        logger.warning(f"Non-owner {performed_by.email} attempted to transfer ownership of organization: {organization.name}")
        raise PermissionDenied("Only owner can transfer ownership")

    if new_owner == organization.owner:
        logger.warning(f"Attempt to transfer ownership to current owner for organization: {organization.name}")
        raise ValidationError("Already owner")

    if not organization.memberships.filter(organization=organization, user=new_owner).exists():
        logger.warning(f"User {new_owner.email} not a member of organization: {organization.name}")
        raise ValidationError("User is not a member of the organization")
    
    new_owner_membership = organization.memberships.get(organization=organization, user=new_owner)
    old_owner_membership = organization.memberships.get(organization=organization, user=performed_by)

    new_owner_membership.role = "OWNER"
    new_owner_membership.save(update_fields=["role"])

    old_owner_membership.role = "ADMIN"
    old_owner_membership.save(update_fields=["role"])
    
    organization.owner = new_owner
    organization.save(update_fields=["owner"])
    logger.info(f"Ownership transferred successfully to {new_owner.email} for organization: {organization.name}")


def delete_organization(*, organization, performed_by):
    logger.info(f"Deleting organization: {organization.name}")
    if organization.owner != performed_by:
        logger.warning(f"Non-owner {performed_by.email} attempted to delete organization: {organization.name}")
        raise PermissionDenied("Only owner can delete")

    organization.is_deleted = True
    organization.save(update_fields=["is_deleted"])
    logger.info(f"Organization deleted successfully: {organization.name}")
