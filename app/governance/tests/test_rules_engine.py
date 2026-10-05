"""
Governance rules engine + the signals that create each container's settings row.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from app.governance.models import OrganizationSettings, ProjectSettings, TeamSettings
from app.governance.services.rules_engine import GovernanceResolver
from app.organizations.models import Organization
from app.projects.models import Project
from app.teams.models import Team
from core.constants.org_constant import ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY
from core.constants.project_constant import PROJECT_ACTION_POLICIES, PROJECT_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ACTION_POLICIES, TEAM_ROLE_HIERARCHY
from core.testing.base import BaseAPITestCase


class SettingsSignalTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()

    def test_each_container_gets_exactly_one_settings_row_on_creation(self):
        org = self.make_org(self.owner)
        team = self.make_team(self.owner)
        project = self.make_project(self.owner)
        self.assertEqual(OrganizationSettings.objects.filter(organization=org).count(), 1)
        self.assertEqual(TeamSettings.objects.filter(team=team).count(), 1)
        self.assertEqual(ProjectSettings.objects.filter(project=project).count(), 1)

    def test_resaving_a_container_does_not_create_another_row(self):
        org = self.make_org(self.owner)
        org.name = "Renamed"
        org.save()
        team = self.make_team(self.owner)
        team.save()
        project = self.make_project(self.owner)
        project.save()
        self.assertEqual(OrganizationSettings.objects.count(), 1)
        self.assertEqual(TeamSettings.objects.count(), 1)
        self.assertEqual(ProjectSettings.objects.count(), 1)

    def test_settings_rows_are_removed_with_their_container(self):
        org = self.make_org(self.owner)
        org.delete()
        self.assertEqual(OrganizationSettings.objects.count(), 0)

    def test_safe_defaults(self):
        """Out of the box only the owner administers members: every delegation flag starts off."""
        org, team, project = self.make_org(self.owner), self.make_team(self.owner), self.make_project(self.owner)
        for cfg in (org.settings, team.settings, project.settings):
            self.assertFalse(cfg.allow_member_invites)
            self.assertFalse(cfg.allow_member_updates)
            self.assertFalse(cfg.allow_member_removal)
            self.assertFalse(cfg.allow_self_removal)
        self.assertEqual((team.settings.max_members, team.settings.max_projects), (20, 10))
        self.assertEqual(project.settings.max_members, 20)
        self.assertEqual(project.settings.default_member_role, "CONTRIBUTOR")
        self.assertEqual(project.settings.create_task_min_role, "MANAGER")
        self.assertTrue(project.settings.allow_task_creation)


class ResolveActionMinRoleTests(SimpleTestCase):
    """The engine clamps a configured threshold into the action's system band."""

    def resolve(self, value, action, policies=PROJECT_ACTION_POLICIES, hierarchy=PROJECT_ROLE_HIERARCHY):
        settings = SimpleNamespace(**{f"{action}_min_role": value})
        return GovernanceResolver.resolve_action_min_role(settings, action, policies, hierarchy)

    def test_a_value_inside_the_band_is_kept(self):
        self.assertEqual(self.resolve("LEAD", "invite_member"), "LEAD")
        self.assertEqual(self.resolve("MANAGER", "invite_member"), "MANAGER")
        self.assertEqual(self.resolve("CONTRIBUTOR", "create_task"), "CONTRIBUTOR")

    def test_a_value_below_the_floor_is_raised(self):
        self.assertEqual(self.resolve("VIEWER", "invite_member"), "LEAD")
        self.assertEqual(self.resolve("GUEST", "create_task"), "CONTRIBUTOR")
        self.assertEqual(self.resolve("CONTRIBUTOR", "delete_task"), "MANAGER")

    def test_a_value_above_the_ceiling_is_lowered(self):
        self.assertEqual(self.resolve("OWNER", "invite_member"), "MANAGER")
        self.assertEqual(self.resolve("OWNER", "create_task"), "MANAGER")

    def test_fixed_bands_always_resolve_to_that_one_role(self):
        for value in ("VIEWER", "MANAGER", "OWNER"):
            self.assertEqual(self.resolve(value, "remove_member"), "MANAGER")
            self.assertEqual(self.resolve(value, "update_member"), "MANAGER")

    def test_org_and_team_policies(self):
        self.assertEqual(self.resolve("VIEWER", "invite_member", ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY), "MANAGER")
        self.assertEqual(self.resolve("OWNER", "invite_member", ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY), "ADMIN")
        self.assertEqual(self.resolve("MEMBER", "create_team", ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY), "MANAGER")
        self.assertEqual(self.resolve("OWNER", "remove_member", TEAM_ACTION_POLICIES, TEAM_ROLE_HIERARCHY), "MANAGER")

    def test_a_missing_setting_falls_back_to_the_policy_default(self):
        result = GovernanceResolver.resolve_action_min_role(SimpleNamespace(), "invite_member",
                                                           PROJECT_ACTION_POLICIES, PROJECT_ROLE_HIERARCHY)
        self.assertEqual(result, "MANAGER")

    def test_a_non_configurable_action_always_uses_its_default(self):
        policies = {"locked": {"system_min_role": "LEAD", "system_max_role": "MANAGER", "configurable": False, "default": "MANAGER"}}
        self.assertEqual(self.resolve("LEAD", "locked", policies), "MANAGER")

    def test_unknown_action_is_an_error(self):
        with self.assertRaises(ValueError):
            self.resolve("LEAD", "launch_missiles")


class EffectiveRulesTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner, allow_member_invites=True, allow_self_removal=True,
                                 allow_member_updates=True, allow_member_removal=False)
        self.team = self.make_team(self.owner, org=self.org, allow_member_invites=False, allow_self_removal=False,
                                   allow_member_updates=False, allow_member_removal=True)

    def project(self, **settings_fields):
        project = self.make_project(self.owner, org=self.org, team=self.team, **settings_fields)
        return Project.objects.get(pk=project.pk)

    def test_without_inheritance_the_projects_own_rules_apply(self):
        project = self.project(allow_member_invites=False, allow_member_updates=True)
        rules = GovernanceResolver.get_effective_project_base_rules(project)
        self.assertFalse(rules["allow_member_invites"])
        self.assertTrue(rules["allow_member_updates"])

    def test_team_rules_override_the_project_when_inherited(self):
        project = self.project(inherit_base_rules_from_team=True, allow_member_removal=False)
        rules = GovernanceResolver.get_effective_project_base_rules(project)
        self.assertTrue(rules["allow_member_removal"])        # from the team
        self.assertFalse(rules["allow_member_updates"])       # from the team

    def test_org_rules_win_over_team_rules(self):
        project = self.project(inherit_base_rules_from_team=True, inherit_base_rules_from_org=True)
        rules = GovernanceResolver.get_effective_project_base_rules(project)
        self.assertTrue(rules["allow_member_invites"])        # org says yes, team says no -> org
        self.assertTrue(rules["allow_member_updates"])
        self.assertFalse(rules["allow_member_removal"])

    def test_inheritance_flags_are_ignored_when_there_is_no_such_container(self):
        project = self.make_project(self.owner, inherit_base_rules_from_team=True, inherit_base_rules_from_org=True,
                                    allow_member_invites=True)
        rules = GovernanceResolver.get_effective_project_base_rules(Project.objects.get(pk=project.pk))
        self.assertTrue(rules["allow_member_invites"])

    def test_every_base_field_is_reported(self):
        rules = GovernanceResolver.get_effective_project_base_rules(self.project())
        self.assertCountEqual(rules, GovernanceResolver.BASE_FIELDS)

    def test_team_rules_inherit_from_the_org_only_when_enabled(self):
        own = GovernanceResolver.get_effective_team_base_rules(self.team)
        self.assertFalse(own["allow_member_invites"])
        self.set_settings(self.team, inherit_base_rules_from_org=True)
        inherited = GovernanceResolver.get_effective_team_base_rules(Team.objects.get(pk=self.team.pk))
        self.assertTrue(inherited["allow_member_invites"])
        self.assertTrue(inherited["allow_self_removal"])
        self.assertCountEqual(inherited, ["allow_member_invites", "allow_self_removal", "require_approval_for_invites"])
        self.assertIsInstance(Organization.objects.get(pk=self.org.pk), Organization)
