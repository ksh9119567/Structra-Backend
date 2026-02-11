from rest_framework.exceptions import PermissionDenied, ValidationError
from app.teams.models import TeamMembership
from app.organizations.models import OrganizationMembership


def transfer_team_ownership(*, team, new_owner, performed_by):
    if team.created_by != performed_by:
        raise PermissionDenied("Only team creator can transfer ownership")

    if new_owner == team.created_by:
        raise ValidationError("User is already the team creator")

    if not OrganizationMembership.objects.filter(
        organization=team.organization,
        user=new_owner
    ).exists():
        raise ValidationError("User is not a member of the organization")

    if not TeamMembership.objects.filter(team=team, user=new_owner).exists():
        raise ValidationError("User is not a member of the team")

    new_owner_membership = TeamMembership.objects.get(
        team=team,
        user=new_owner
    )
    new_owner_membership.role = "MANAGER"
    new_owner_membership.save(update_fields=["role"])

    team.created_by = new_owner
    team.save(update_fields=["created_by"])


def delete_team(*, team, performed_by):
    if team.created_by != performed_by:
        raise PermissionDenied("Only team creator can delete team")

    team.delete()
