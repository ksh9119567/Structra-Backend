import logging

from django.db import transaction

from rest_framework.exceptions import PermissionDenied, ValidationError

from app.teams.models import TeamMembership
from app.organizations.models import OrganizationMembership
from app.projects.services.project_team_service import unassign_team

from core.permissions.resolver import is_team_governance_backstop

logger = logging.getLogger(__name__)


def transfer_team_ownership(*, team, new_owner, performed_by):
    logger.info(f"Transferring ownership of team: {team.name} to {new_owner.email}")
    # The team creator may transfer; so may the owner of the organization the
    # team belongs to (the governance backstop for continuity). This used to
    # reject the org owner on every path.
    if team.created_by != performed_by and not is_team_governance_backstop(performed_by, team):
        logger.warning(f"Unauthorized ownership transfer attempt by {performed_by.email} for team: {team.name}")
        raise PermissionDenied("Only team creator or organization owner can transfer ownership")

    if new_owner == team.created_by:
        logger.warning(f"Attempt to transfer ownership to current creator for team: {team.name}")
        raise ValidationError("User is already the team creator")

    if team.organization and not OrganizationMembership.objects.filter(organization=team.organization, user=new_owner).exists():
        logger.warning(f"User {new_owner.email} not a member of organization for team: {team.name}")
        raise ValidationError("User is not a member of the organization")

    if not TeamMembership.objects.filter(team=team, user=new_owner).exists():
        logger.warning(f"User {new_owner.email} not a member of team: {team.name}")
        raise ValidationError("User is not a member of the team")

    new_owner_membership = TeamMembership.objects.get(team=team, user=new_owner)
    old_owner_membership = team.memberships.get(user=team.created_by)

    with transaction.atomic():
        old_owner_membership.role = "MANAGER"
        old_owner_membership.save(update_fields=["role"])

        new_owner_membership.role = "OWNER"
        new_owner_membership.save(update_fields=["role"])

        team.created_by = new_owner
        team.save(update_fields=["created_by"])
    logger.info(f"Ownership transferred successfully to {new_owner.email} for team: {team.name}")


def delete_team(*, team, performed_by):
    logger.info(f"Deleting team: {team.name}")
    if team.created_by != performed_by and not is_team_governance_backstop(performed_by, team):
        logger.warning(f"Unauthorized delete attempt by {performed_by.email} for team: {team.name}")
        raise PermissionDenied("Only the team creator or the organization owner can delete the team")

    with transaction.atomic():
        # A soft-deleted team must stop granting its members access to the
        # projects it was assigned to. Unassign through the service so that,
        # if this was a project's owning team, the next team is promoted.
        for link in list(team.project_links.select_related("project")):
            unassign_team(project=link.project, team=team)

        team.is_deleted = True
        team.save(update_fields=["is_deleted"])
    logger.info(f"Team deleted successfully: {team.name}")
