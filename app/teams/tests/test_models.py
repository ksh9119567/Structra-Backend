from django.db import IntegrityError, transaction

from app.governance.models import TeamSettings
from app.teams.models import TeamMembership
from core.testing.base import BaseAPITestCase


class TeamModelTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.team = self.make_team(self.owner)

    def test_str(self):
        self.assertEqual(str(self.team), self.team.name)

    def test_settings_row_is_created_automatically(self):
        self.assertTrue(TeamSettings.objects.filter(team=self.team).exists())

    def test_membership_is_unique_per_user_and_team(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TeamMembership.objects.create(team=self.team, user=self.owner, role="VIEWER")

    def test_membership_role_defaults_from_team_settings(self):
        membership = TeamMembership(team=self.team, user=self.make_user(), role="")
        membership.save()
        self.assertEqual(membership.role, self.team.settings.default_member_role)

    def test_standalone_team_has_no_organization(self):
        self.assertIsNone(self.team.organization)

    def test_projects_property_only_lists_live_assigned_projects(self):
        live = self.make_project(self.owner, team=self.team)
        dead = self.make_project(self.owner, team=self.team)
        dead.is_deleted = True
        dead.save()
        self.make_project(self.owner)  # not assigned
        self.assertEqual(list(self.team.projects), [live])

    def test_deleting_a_team_cascades_to_memberships(self):
        self.team.delete()
        self.assertEqual(TeamMembership.objects.count(), 0)
