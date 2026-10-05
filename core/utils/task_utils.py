import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import NotFound, ValidationError

from app.tasks.models import Task

logger = logging.getLogger(__name__)

def get_task(task_id):
    """
    Returns a task instance by task_id.
    Raises NotFound (404) for a missing, soft-deleted or malformed id.
    """
    logger.debug(f"Getting task: {task_id}")
    if not task_id:
        logger.warning("Task ID is required but not provided")
        raise ValidationError("Task ID is required")

    try:
        obj = Task.objects.filter(id=task_id, is_deleted=False).first()
    except (DjangoValidationError, ValueError):
        obj = None  # malformed UUID
    if not obj:
        logger.warning(f"Task not found: {task_id}")
        raise NotFound("Task not found")
    logger.debug(f"Task found: {obj.title}")
    return obj

def get_all_task(project):
    """
    Returns the live (non-deleted) tasks of a project.
    """
    if project:
        # Explicit, stable order: Task has no default ordering, so paginating an
        # unordered queryset can repeat or skip rows between pages.
        return Task.objects.filter(project=project, is_deleted=False).order_by("created_at", "id")
    raise ValidationError("Project ID is required")
