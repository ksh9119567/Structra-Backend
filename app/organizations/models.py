import uuid

from django.db import models
from django.utils import timezone

from app.governance.models import OrganizationSettings

from core.constants.org_constant import ORG_ROLES
from core.models import TimeStampedModel

class Organization(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,  # prevent accidental deletion
        related_name="owned_organizations"
    )

    members = models.ManyToManyField(
        "accounts.User",
        through="OrganizationMembership",
        related_name="organizations"
    )

    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    
    class Meta:
        ordering = ("name",)
    
    def __str__(self):
        return self.name


class OrganizationMembership(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(max_length=50, choices=ORG_ROLES, null=False, blank=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_org_user")
        ]
        ordering = ("-joined_at",)
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["organization"]),
        ]
        
    def save(self, *args, **kwargs):
        if not self.role:
            org_settings = OrganizationSettings.objects.get(organization=self.organization)
            self.role = org_settings.default_member_role
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.organization.name}"
