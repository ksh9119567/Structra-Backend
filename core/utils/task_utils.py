import logging

from rest_framework.exceptions import NotFound, ValidationError

from app.tasks.models import Task

logger = logging.getLogger(__name__)

def get_task(task_id):
    """
    Returns a task instance by task_id.
    """
    logger.debug(f"Getting task: {task_id}")
    if task_id:
        try:
            obj = Task.objects.filter(id=task_id, is_deleted=False).first()
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
            return Task.objects.filter(project = project, is_deleted=False)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Project ID is required")