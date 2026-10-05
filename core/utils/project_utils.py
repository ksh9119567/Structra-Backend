import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import NotFound, ValidationError

from app.projects.models import Project, ProjectMembership
from app.teams.models import TeamMembership
from app.organizations.models import OrganizationMembership

logger = logging.getLogger(__name__)


def count_explicit_members(project):
    """
    Counts ProjectMembership rows toward the configurable member limit,
    excluding anyone already covered by any assigned team's roster - per
    the doc, only members who aren't on an assigned team count.
    """
    team_ids = [link.team_id for link in project.all_team_links]
    team_member_ids = set()
    if team_ids:
        team_member_ids = set(
            TeamMembership.objects.filter(team_id__in=team_ids).values_list("user_id", flat=True)
        )
    return project.memberships.exclude(user_id__in=team_member_ids).count()


def get_stale_explicit_members(project):
    """
    Explicit ProjectMembership rows whose user is no longer part of any
    container that would justify their access - the project's organization
    (if any) or any currently assigned team (if any). Team-derived access
    needs no such check: it's computed live in effective_role(), so leaving
    a team removes it automatically already - this is the one offboarding
    gap that isn't automatic.
    """
    if not project.organization_id and not project.all_team_links:
        return ProjectMembership.objects.none()

    affiliated_user_ids = set()
    if project.organization_id:
        affiliated_user_ids |= set(
            OrganizationMembership.objects.filter(
                organization_id=project.organization_id
            ).values_list("user_id", flat=True)
        )
    team_ids = [link.team_id for link in project.all_team_links]
    if team_ids:
        affiliated_user_ids |= set(
            TeamMembership.objects.filter(team_id__in=team_ids).values_list("user_id", flat=True)
        )

    return project.memberships.exclude(user_id__in=affiliated_user_ids).exclude(user_id=project.created_by_id)


def get_project(project_id):
    """
    Returns a project instance by project_id.
    Raises NotFound (404) for a missing, soft-deleted or malformed id.
    """
    logger.debug(f"Getting project: {project_id}")
    if not project_id:
        logger.warning("Project ID is required but not provided")
        raise ValidationError("Project ID is required")

    try:
        obj = Project.objects.filter(id=project_id, is_deleted=False).first()
    except (DjangoValidationError, ValueError):
        obj = None  # malformed UUID
    if not obj:
        logger.warning(f"Project not found: {project_id}")
        raise NotFound("Project not found")
    logger.debug(f"Project found: {obj.name}")
    return obj

def get_all_project_memberships(project_id):
    """
    Returns all members of a project by project_id.
    """
    if project_id:
        return ProjectMembership.objects.filter(project=project_id)
    raise ValidationError("Project ID is required")

def get_project_membership(project_id, user):
    """
    Returns a membership instance by project_id and user.
    Raises NotFound when the user has no explicit membership on the project.
    """
    if project_id and user:
        try:
            return ProjectMembership.objects.get(project=project_id, user=user)
        except ProjectMembership.DoesNotExist:
            raise NotFound("Project membership not found")
    raise ValidationError("Project ID and user are required")
