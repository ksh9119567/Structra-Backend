import logging

from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from app.tasks.models import Task

from core.permissions.base import get_project_role

logger = logging.getLogger(__name__)

def delete_task(*, task, performed_by):
    logger.info(f"Deleting task: {task.title} by user: {performed_by.email}")
    if task.created_by != performed_by:
        logger.warning(f"Non-creator {performed_by.email} attempted to delete task: {task.title}")
        raise PermissionDenied("Only task creator can delete task")
    
    role = get_project_role(performed_by, task.project)
    if role not in ["OWNER", "MANAGER"]:
        logger.warning(f"User {performed_by.email} with role {role} attempted to delete task: {task.title}")
        raise PermissionDenied("You do not have permission to delete this task.")
    
    task.delete()
    logger.info(f"Task deleted successfully: {task.title}")