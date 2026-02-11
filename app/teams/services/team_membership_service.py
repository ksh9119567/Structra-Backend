from rest_framework.exceptions import ValidationError, PermissionDenied
from app.teams.models import TeamMembership


def add_team_member(*, team, user, role):
    if TeamMembership.objects.filter(team=team, user=user).exists():
        raise ValidationError("User already a member")

    return TeamMembership.objects.create(
        team=team,
        user=user,
        role=role
    )


def remove_team_member(*, team, user):
    if user == team.created_by:
        raise PermissionDenied("Cannot remove team creator")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()


def self_remove_team_member(*, team, user):
    if not team.is_self_remove_allowed:
        raise PermissionDenied("Self removal not allowed")

    if user == team.created_by:
        raise PermissionDenied("Team creator cannot remove themselves")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()


def update_team_member_role(*, team, user, role):
    membership = TeamMembership.objects.get(team=team, user=user)
    membership.role = role
    membership.save(update_fields=["role"])
    return membership
