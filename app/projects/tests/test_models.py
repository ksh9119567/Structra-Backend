from django.db import IntegrityError, transaction

from app.governance.models import ProjectSettings
from app.projects.models import Project, ProjectMembership, ProjectTeam
from app.projects.services.project_team_service import assign_team
from core.testing.base import BaseAPITestCase


class ProjectModelTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)

    def test_str(self):
        self.assertEqual(str(self.project), self.project.name)

    def test_settings_row_is_created_automatically(self):
        self.assertTrue(ProjectSettings.objects.filter(project=self.project).exists())

    def test_status_defaults_to_planning_and_not_deleted(self):
        self.assertEqual(self.project.status, "PLANNING")
        self.assertFalse(self.project.is_deleted)

    def test_membership_is_unique_per_user_and_project(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMembership.objects.create(project=self.project, user=self.owner, role="VIEWER")

    def test_membership_role_defaults_from_project_settings(self):
        user = self.make_user()
        membership = ProjectMembership(project=self.project, user=user, role="")
        membership.save()
        self.assertEqual(membership.role, self.project.settings.default_member_role)

    def test_creator_cannot_be_deleted_while_projects_exist(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.owner.delete()

    def test_team_properties_without_a_team(self):
        self.assertIsNone(self.project.team)
        self.assertIsNone(self.project.team_id)
        self.assertIsNone(self.project.team_link)
        self.assertEqual(self.project.all_team_links, [])


class ProjectTeamLinkTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)
        self.team_a = self.make_team(self.make_user())
        self.team_b = self.make_team(self.make_user())

    def test_team_property_reads_the_owning_link(self):
        assign_team(project=self.project, team=self.team_a, role="LEAD", is_owning=True, assigned_by=self.owner)
        assign_team(project=self.project, team=self.team_b, role="VIEWER", is_owning=False, assigned_by=self.owner)
        project = Project.objects.get(pk=self.project.pk)
        self.assertEqual(project.team, self.team_a)
        self.assertEqual(project.team_id, self.team_a.id)
        self.assertEqual(project.team_link.role, "LEAD")
        self.assertEqual(len(project.all_team_links), 2)

    def test_a_team_can_be_linked_to_a_project_only_once(self):
        ProjectTeam.objects.create(project=self.project, team=self.team_a, role="VIEWER", is_owning=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectTeam.objects.create(project=self.project, team=self.team_a, role="LEAD", is_owning=False)

    def test_database_allows_at_most_one_owning_team_per_project(self):
        ProjectTeam.objects.create(project=self.project, team=self.team_a, role="VIEWER", is_owning=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectTeam.objects.create(project=self.project, team=self.team_b, role="VIEWER", is_owning=True)

    def test_database_allows_many_non_owning_teams(self):
        ProjectTeam.objects.create(project=self.project, team=self.team_a, role="VIEWER", is_owning=True)
        ProjectTeam.objects.create(project=self.project, team=self.team_b, role="VIEWER", is_owning=False)
        self.assertEqual(self.project.team_links.count(), 2)

    def test_owning_flag_is_per_project(self):
        other = self.make_project(self.owner)
        ProjectTeam.objects.create(project=self.project, team=self.team_a, role="VIEWER", is_owning=True)
        ProjectTeam.objects.create(project=other, team=self.team_a, role="VIEWER", is_owning=True)
        self.assertEqual(ProjectTeam.objects.filter(is_owning=True).count(), 2)

    def test_team_projects_property_lists_assigned_live_projects(self):
        assign_team(project=self.project, team=self.team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        deleted = self.make_project(self.owner)
        assign_team(project=deleted, team=self.team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        deleted.is_deleted = True
        deleted.save()
        self.assertEqual(list(self.team_a.projects), [self.project])

    def test_deleting_a_project_cascades_to_its_links_and_memberships(self):
        assign_team(project=self.project, team=self.team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.project.delete()
        self.assertEqual(ProjectTeam.objects.count(), 0)
        self.assertEqual(ProjectMembership.objects.count(), 0)
