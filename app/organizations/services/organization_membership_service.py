from rest_framework.exceptions import ValidationError, PermissionDenied
from organizations.models import OrganizationMembership


def add_member(*, organization, user, role):
    if OrganizationMembership.objects.filter(
        organization=organization, user=user
    ).exists():
        raise ValidationError("User already a member")

    return OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=role
    )


def remove_member(*, organization, user):
    if user == organization.owner:
        raise PermissionDenied("Cannot remove owner")

    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.delete()


def self_remove(*, organization, user):
    if not organization.is_self_remove_allowed:
        raise PermissionDenied("Self remove not allowed")

    if user == organization.owner:
        raise PermissionDenied("Owner cannot remove self")

    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.delete()


def update_role(*, organization, user, role):
    membership = OrganizationMembership.objects.get(
        organization=organization,
        user=user
    )
    membership.role = role
    membership.save()
    return membership
