from django.db.models.signals import post_save
from django.dispatch import receiver

from app.organizations.models import Organization
from app.teams.models import Team
from app.projects.models import Project

from app.governance.models import (
    OrganizationSettings,
    TeamSettings,
    ProjectSettings,
)


# =========================================================
# ORGANIZATION SETTINGS AUTO-CREATE
# =========================================================

@receiver(post_save, sender=Organization)
def create_organization_settings(sender, instance, created, **kwargs):
    if created:
        OrganizationSettings.objects.create(organization=instance)


# =========================================================
# TEAM SETTINGS AUTO-CREATE
# =========================================================

@receiver(post_save, sender=Team)
def create_team_settings(sender, instance, created, **kwargs):
    if created:
        TeamSettings.objects.create(team=instance)


# =========================================================
# PROJECT SETTINGS AUTO-CREATE
# =========================================================

@receiver(post_save, sender=Project)
def create_project_settings(sender, instance, created, **kwargs):
    if created:
        ProjectSettings.objects.create(project=instance)
