import uuid

from django.db import models

from app.governance.models import ProjectSettings

from core.constants.project_constant import PROJECT_ROLES, PROJECT_STATUS
from core.models import TimeStampedModel


class Project(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="projects"
    )

    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects"
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_projects"
    )

    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=PROJECT_STATUS, default="PLANNING")

    members = models.ManyToManyField(
        "accounts.User",
        through="ProjectMembership",
        related_name="projects"
    )
    
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    
    class Meta:
        ordering = ("name", )
    
    def __str__(self):
        return self.name


class ProjectMembership(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="project_memberships"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(max_length=50, choices=PROJECT_ROLES, null=False, blank=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "project"], name="unique_project_user")
        ]
        ordering = ("-joined_at",)
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["project"]),
        ]

    def save(self, *args, **kwargs):
        if not self.role:
            project_settings = ProjectSettings.objects.get(project=self.project)
            self.role = project_settings.default_member_role
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} - {self.project.name}"
