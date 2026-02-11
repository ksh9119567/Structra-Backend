import uuid

from django.db import models

from core.constants import TASK_STATUS, TASK_PRIORITY, TASK_TYPE
from core.models import TimeStampedModel

class Task(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks"
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, default="", max_length=2000)
    start_date = models.DateField(blank=True, null=True, default=None)
    due_date = models.DateField(blank=True, null=True, default=None)
    status = models.CharField(max_length=50, choices=TASK_STATUS, default="TO_DO")
    priority = models.CharField(max_length=50, choices=TASK_PRIORITY, default="MEDIUM")
    task_type = models.CharField(max_length=50, choices=TASK_TYPE, default="FEATURE")
    
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_tasks"
    )
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"
    

    
    
    
    