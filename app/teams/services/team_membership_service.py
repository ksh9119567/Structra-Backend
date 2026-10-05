import logging

from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from app.teams.models import TeamMembership

from core.permissions.base import get_team_role
from core.permissions.resolver import team_member_admin_role
from core.constants.team_constant import TEAM_ROLE_HIERARCHY

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


def remove_team_member(*, team, user, performed_by):
    logger.info(f"Removing member {user.email} from team: {team.name}")
    if user == team.created_by:
        logger.warning(f"Attempt to remove team creator from team: {team.name}")
        raise PermissionDenied("Cannot remove team creator")

    target_user_role = get_team_role(user, team)
    if target_user_role is None:
        logger.warning(f"Attempt to remove non-member {user.email} from team: {team.name}")
        raise ValidationError("User is not a member of this team")

    # An org owner (governance backstop) acts with team-Owner authority even
    # though they need not be a member of the team themselves.
    action_user_role = team_member_admin_role(performed_by, team)

    if TEAM_ROLE_HIERARCHY.get(target_user_role, -1) >= TEAM_ROLE_HIERARCHY.get(action_user_role, -1):
        logger.warning(f"Attempt to remove user with equal or higher role from team: {team.name}")
        raise PermissionDenied("Cannot remove user with equal or higher role")

    if target_user_role == "MANAGER":
        manager_count = team.memberships.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Last manager attempted removal from team: {team.name}")
            raise PermissionDenied("Last manager cannot be removed")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()
    logger.info(f"Member {user.email} removed successfully from team: {team.name}")


def self_remove_team_member(*, team, user):
    logger.info(f"Self-remove requested by {user.email} from team: {team.name}")
    user_role = get_team_role(user, team)

    if not team.settings.allow_self_removal:
        logger.warning(f"Self-remove not allowed for team: {team.name}")
        raise PermissionDenied("Self removal not allowed")

    if user == team.created_by:
        logger.warning(f"Team owner attempted self-remove from team: {team.name}")
        raise PermissionDenied("Team owner cannot remove themselves")

    if user_role == "MANAGER":
        manager_count = team.memberships.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Last manager attempted self-remove from team: {team.name}")
            raise PermissionDenied("Last manager cannot remove themselves.")

    membership = TeamMembership.objects.get(team=team, user=user)
    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from team: {team.name}")


def update_team_member_role(*, team, user, role):
    logger.info(f"Updating role for {user.email} in team: {team.name} to {role}")
    try:
        membership = TeamMembership.objects.get(team=team, user=user)
    except TeamMembership.DoesNotExist:
        raise NotFound("User is not a member of this team")
    membership.role = role
    membership.save(update_fields=["role"])
    logger.info(f"Role updated successfully for {user.email} in team: {team.name}")
    return membership
