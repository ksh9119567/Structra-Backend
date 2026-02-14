import logging
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from app.accounts.models import User
from app.organizations.models import Organization, OrganizationMembership
from app.teams.models import Team, TeamMembership
from app.projects.models import Project, ProjectMembership
from app.tasks.models import Task

logger = logging.getLogger(__name__)


def get_user(identifier, kind="email"):
    """
    Returns a user instance by email or phone number.
    """
    logger.debug(f"Getting user by {kind}: {identifier}")
    if identifier:
        try:
            if kind == "email":
                user = User.objects.filter(email__iexact=identifier).first()
            elif kind == "phone":
                user = User.objects.filter(phone_no=identifier).first()
            if user:
                logger.debug(f"User found: {user.id}")
            else:
                logger.warning(f"User not found for {kind}: {identifier}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by {kind}: {identifier}, error: {str(e)}")
            raise ValidationError("User not found")
    logger.warning("User ID is required but not provided")
    raise ValidationError("User ID is required")
    
def get_org(org_id):
    """
    Returns a organization instance by org_id.
    """
    logger.debug(f"Getting organization: {org_id}")
    if org_id:
        try:
            obj = Organization.objects.filter(id=org_id).first()
            if not obj:
                logger.warning(f"Organization not found: {org_id}")
                raise NotFound("Organization not found")
            logger.debug(f"Organization found: {obj.name}")
            return obj
        except Exception as e:
            logger.error(f"Error getting organization {org_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Organization ID is required but not provided")
    raise ValidationError("Organization ID is required")

def get_org_membership(org_id, user):
    """
    Returns a membership instance by org_id and user.
    """
    if org_id and user:
        try:
            obj = OrganizationMembership.objects.get(organization_id=org_id, user=user)
            if not obj:
                raise NotFound("Organization not found")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID and user are required")

def get_all_org_memberships(org_id):
    """
    Returns all members of an organization by org_id.
    """
    if org_id:
        try:
            return OrganizationMembership.objects.filter(organization_id=org_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID is required")

def get_team(team_id):
    """
    Returns a team instance by team_id.
    """
    logger.debug(f"Getting team: {team_id}")
    if team_id:
        try:
            obj = Team.objects.filter(id=team_id).first()
            if not obj:
                logger.warning(f"Team not found: {team_id}")
                raise NotFound("Team not found")
            logger.debug(f"Team found: {obj.name}")
            return obj
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Team ID is required but not provided")
    raise ValidationError("Team ID is required")

def get_all_team_memberships(team_id):
    """
    Returns all members of a team by team_id.
    """
    if team_id:
        try:
            return TeamMembership.objects.filter(team_id=team_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID is required")

def get_team_membership(team_id, user):
    """
    Returns a membership instance by team_id and user.
    """
    if team_id and user:
        try:
            obj = TeamMembership.objects.get(team_id=team_id, user=user)
            if not obj:
                raise ValidationError("User is not a member of this team")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID and user are required")

def get_project(project_id):
    """
    Returns a project instance by project_id".
    """
    logger.debug(f"Getting project: {project_id}")
    if project_id:
        try:
            obj = Project.objects.filter(id = project_id).first()
            if not obj:
                logger.warning(f"Project not found: {project_id}")
                raise NotFound("Project not found")
            logger.debug(f"Project found: {obj.name}")
            return obj
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Project ID is required but not provided")
    raise ValidationError("Project ID is required")

def get_all_project_memberships(project_id):
    """
    Returns all members of a project by project_id.
    """
    if project_id:
        try:
            return ProjectMembership.objects.filter(project=project_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Project ID os required")

def get_project_membership(project_id, user):
    """
    Returns a membership instance by team_id and user.
    """
    if project_id and user:
        try:
            obj = ProjectMembership.objects.get(project=project_id, user=user)
            if not obj:
                raise ValidationError("user is not a member of this project")
            return obj
        except Exception as e:
            raise Exception(e)
    raise ValidationError("project ID and user are required")


def get_task(task_id):
    """
    Returns a task instance by task_id.
    """
    logger.debug(f"Getting task: {task_id}")
    if task_id:
        try:
            obj = Task.objects.filter(id=task_id).first()
            if not obj:
                logger.warning(f"Task not found: {task_id}")
                raise NotFound("Task not found")
            logger.debug(f"Task found: {obj.title}")
            return obj
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Task ID is required but not provided")
    raise ValidationError("Task ID is required")

def get_all_task(project):
    """
    Returns a list of tasks by project_id.
    """
    if project:
        try:
            return Task.objects.filter(project = project)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Project ID is required")

