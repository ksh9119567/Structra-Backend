from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from app.tasks.models import Task

from core.permissions.base import get_project_role

def delete_task(*, task, performed_by):
    if task.created_by !=performed_by:
        raise PermissionDenied("Only task creator can delete task")
    
    role = get_project_role(performed_by, task.project)
    if role not in ["OWNER", "MANAGER"]:
        raise PermissionDenied("You do not have permission to delete this task.")
    
    task.delete()