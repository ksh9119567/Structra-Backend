import logging

from rest_framework.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


def transfer_ownership(*, organization, new_owner, performed_by):
    logger.info(f"Transferring ownership of organization: {organization.name} to {new_owner.email}")
    if organization.owner != performed_by:
        logger.warning(f"Non-owner {performed_by.email} attempted to transfer ownership of organization: {organization.name}")
        raise PermissionDenied("Only owner can transfer ownership")

    if new_owner == organization.owner:
        logger.warning(f"Attempt to transfer ownership to current owner for organization: {organization.name}")
        raise ValidationError("Already owner")

    organization.owner = new_owner
    organization.save(update_fields=["owner"])
    logger.info(f"Ownership transferred successfully to {new_owner.email} for organization: {organization.name}")


def delete_organization(*, organization, performed_by):
    logger.info(f"Deleting organization: {organization.name}")
    if organization.owner != performed_by:
        logger.warning(f"Non-owner {performed_by.email} attempted to delete organization: {organization.name}")
        raise PermissionDenied("Only owner can delete")

    organization.delete()
    logger.info(f"Organization deleted successfully: {organization.name}")
