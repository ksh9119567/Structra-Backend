"""
Data-integrity tests for the role ladder and the per-scope role / policy tables.
A typo in one of these silently breaks permission checks, so they are pinned here.
"""
from django.test import SimpleTestCase

from core.constants.org_constant import ORG_ACTION_POLICIES, ORG_ROLES, ORG_ROLE_HIERARCHY
from core.constants.project_constant import PROJECT_ACTION_POLICIES, PROJECT_ROLES, PROJECT_ROLE_HIERARCHY
from core.constants.role_ladder import ROLE_LADDER, build_hierarchy
from core.constants.task_constant import TASK_PRIORITY, TASK_STATUS, TASK_TYPE
from core.constants.team_constant import TEAM_ACTION_POLICIES, TEAM_ROLES, TEAM_ROLE_HIERARCHY

SCOPES = {
    "org": (ORG_ROLES, ORG_ROLE_HIERARCHY, ORG_ACTION_POLICIES),
    "team": (TEAM_ROLES, TEAM_ROLE_HIERARCHY, TEAM_ACTION_POLICIES),
    "project": (PROJECT_ROLES, PROJECT_ROLE_HIERARCHY, PROJECT_ACTION_POLICIES),
}


class RoleLadderTests(SimpleTestCase):
    def test_ladder_order(self):
        order = ["GUEST", "VIEWER", "CONTRIBUTOR", "LEAD", "MANAGER", "ADMIN", "OWNER"]
        ranks = [ROLE_LADDER[r] for r in order]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))

    def test_member_and_contributor_are_the_same_tier(self):
        self.assertEqual(ROLE_LADDER["MEMBER"], ROLE_LADDER["CONTRIBUTOR"])

    def test_guest_is_the_floor_and_owner_the_ceiling(self):
        self.assertEqual(min(ROLE_LADDER.values()), ROLE_LADDER["GUEST"])
        self.assertEqual(max(ROLE_LADDER.values()), ROLE_LADDER["OWNER"])

    def test_build_hierarchy_uses_the_shared_ranks(self):
        self.assertEqual(build_hierarchy([("OWNER", "Owner"), ("VIEWER", "Viewer")]), {"OWNER": 100, "VIEWER": 10})

    def test_build_hierarchy_rejects_a_role_with_no_ladder_entry(self):
        with self.assertRaises(ValueError):
            build_hierarchy([("OWNER", "Owner"), ("SUPERHERO", "Superhero")])


class ScopeTableTests(SimpleTestCase):
    def test_each_hierarchy_covers_exactly_its_roles(self):
        for scope, (roles, hierarchy, _policies) in SCOPES.items():
            self.assertCountEqual(hierarchy, [r[0] for r in roles], scope)

    def test_every_scope_has_an_owner_on_top(self):
        for scope, (_roles, hierarchy, _policies) in SCOPES.items():
            self.assertEqual(max(hierarchy, key=hierarchy.get), "OWNER", scope)

    def test_project_roles_include_guest_but_org_and_team_do_not(self):
        self.assertIn("GUEST", PROJECT_ROLE_HIERARCHY)
        self.assertNotIn("GUEST", ORG_ROLE_HIERARCHY)
        self.assertNotIn("GUEST", TEAM_ROLE_HIERARCHY)

    def test_roles_are_comparable_across_scopes(self):
        self.assertGreater(TEAM_ROLE_HIERARCHY["MANAGER"], PROJECT_ROLE_HIERARCHY["LEAD"])
        self.assertEqual(TEAM_ROLE_HIERARCHY["MEMBER"], PROJECT_ROLE_HIERARCHY["CONTRIBUTOR"])
        self.assertEqual(ORG_ROLE_HIERARCHY["OWNER"], PROJECT_ROLE_HIERARCHY["OWNER"])

    def test_action_policies_are_well_formed(self):
        for scope, (_roles, hierarchy, policies) in SCOPES.items():
            for action, policy in policies.items():
                where = f"{scope}.{action}"
                for key in ("system_min_role", "system_max_role", "configurable", "default"):
                    self.assertIn(key, policy, where)
                for key in ("system_min_role", "system_max_role", "default"):
                    self.assertIn(policy[key], hierarchy, f"{where}.{key} is not a role of this scope")
                self.assertLessEqual(hierarchy[policy["system_min_role"]], hierarchy[policy["system_max_role"]], where)
                self.assertGreaterEqual(hierarchy[policy["default"]], hierarchy[policy["system_min_role"]], where)
                self.assertLessEqual(hierarchy[policy["default"]], hierarchy[policy["system_max_role"]], where)

    def test_policy_actions_match_the_settings_fields_that_configure_them(self):
        # resolve_action_min_role reads `<action>_min_role` from the settings model.
        from app.governance.models import OrganizationSettings, ProjectSettings, TeamSettings
        models = {"org": OrganizationSettings, "team": TeamSettings, "project": ProjectSettings}
        for scope, (_roles, _hierarchy, policies) in SCOPES.items():
            fields = {f.name for f in models[scope]._meta.get_fields()}
            for action in policies:
                self.assertIn(f"{action}_min_role", fields, f"{scope}.{action}")

    def test_no_action_can_be_delegated_above_what_its_ceiling_allows_to_owner_only(self):
        # OWNER is never a legal delegation target - ownership is not delegable.
        for scope, (_roles, _hierarchy, policies) in SCOPES.items():
            for action, policy in policies.items():
                self.assertNotEqual(policy["system_max_role"], "OWNER", f"{scope}.{action}")
                self.assertNotEqual(policy["default"], "OWNER", f"{scope}.{action}")

    def test_task_choice_tables(self):
        self.assertEqual([c[0] for c in TASK_STATUS], ["TO_DO", "IN_PROGRESS", "REVIEW", "DONE", "BLOCKED"])
        self.assertEqual([c[0] for c in TASK_PRIORITY], ["LOW", "MEDIUM", "HIGH", "URGENT"])
        self.assertEqual([c[0] for c in TASK_TYPE], ["BUG", "FEATURE", "IMPROVEMENT", "DOCUMENTATION"])
