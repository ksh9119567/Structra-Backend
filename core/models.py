import uuid
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityLog(models.Model):
    """
    Model to track user activities across the application
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ACCESS', 'Access'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities'
    )
    username = models.CharField(max_length=255, blank=True, help_text="Stored for record keeping even if user is deleted")
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    resource_type = models.CharField(max_length=100, blank=True, db_index=True, help_text="e.g., Organization, Project, Task")
    resource_id = models.CharField(max_length=255, blank=True, db_index=True)
    resource_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    
    # Request details
    method = models.CharField(max_length=10, db_index=True)
    path = models.CharField(max_length=500, db_index=True)
    query_params = models.JSONField(null=True, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    
    # Response details
    status_code = models.IntegerField(db_index=True)
    response_time_ms = models.FloatField(null=True, blank=True)
    
    # Client details
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    extra_data = models.JSONField(null=True, blank=True, help_text="Additional context-specific data")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'user']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', 'status_code']),
        ]
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.username or 'Anonymous'} - {self.action} - {self.resource_type} - {self.timestamp}"
