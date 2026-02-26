import logging

from rest_framework.exceptions import NotFound, ValidationError

from app.projects.models import Project, ProjectMembership

logger = logging.getLogger(__name__)


def get_project(project_id):
    """
    Returns a project instance by project_id".
    """
    logger.debug(f"Getting project: {project_id}")
    if project_id:
        try:
            obj = Project.objects.filter(id = project_id, is_deleted=False).first()
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
