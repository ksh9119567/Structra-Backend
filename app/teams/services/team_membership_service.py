import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.teams.models import TeamMembership

logger = logging.getLogger(__name__)


def add_team_member(*, team, user, role):
    logger.info(f"Adding member {user.email} to team: {team.name} with role: {role}")
    if TeamMembership.objects.filter(team=team, user=user).exists():
        logger.warning(f"User {user.email} already a member of team: {team.name}")
        raise ValidationError("User already a member")

    membership = TeamMembership.objects.create(
        team=team,
        user=user,
        role=role
    )
    logger.info(f"Member {user.email} added successfully to team: {team.name}")
    return membership


def remove_team_member(*, team, user):
    logger.info(f"Removing member {user.email} from team: {team.name}")
    if user == team.created_by:
        logger.warning(f"Attempt to remove team creator from team: {team.name}")
        raise PermissionDenied("Cannot remove team creator")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from team: {team.name}")


def self_remove_team_member(*, team, user):
    logger.info(f"Self-remove requested by {user.email} from team: {team.name}")
    if not team.is_self_remove_allowed:
        logger.warning(f"Self-remove not allowed for team: {team.name}")
        raise PermissionDenied("Self removal not allowed")

    if user == team.created_by:
        logger.warning(f"Team creator attempted self-remove from team: {team.name}")
        raise PermissionDenied("Team creator cannot remove themselves")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from team: {team.name}")


def update_team_member_role(*, team, user, role):
    logger.info(f"Updating role for {user.email} in team: {team.name} to {role}")
    membership = TeamMembership.objects.get(team=team, user=user)
    membership.role = role
    membership.save(update_fields=["role"])
    logger.info(f"Role updated successfully for {user.email} in team: {team.name}")
    return membership
