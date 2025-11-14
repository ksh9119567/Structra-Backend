import uuid

from django.db import models
from django.utils import timezone

from core.constants import ORG_ROLES
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
    role = models.CharField(max_length=50, choices=ORG_ROLES)
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

    def __str__(self):
        return f"{self.user.email} - {self.organization.name}"
