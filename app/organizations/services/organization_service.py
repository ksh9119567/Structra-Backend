from rest_framework.exceptions import PermissionDenied, ValidationError


def transfer_ownership(*, organization, new_owner, performed_by):
    if organization.owner != performed_by:
        raise PermissionDenied("Only owner can transfer ownership")

    if new_owner == organization.owner:
        raise ValidationError("Already owner")

    organization.owner = new_owner
    organization.save(update_fields=["owner"])


def delete_organization(*, organization, performed_by):
    if organization.owner != performed_by:
        raise PermissionDenied("Only owner can delete")

    organization.delete()
