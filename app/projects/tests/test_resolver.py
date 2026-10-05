"""
Unit tests for the access-resolution layer (core/permissions/resolver.py and
core/utils/project_utils.py): who is Owner, who is a governance backstop, and
how explicit membership and team-derived access combine.
"""
from django.contrib.auth.models import AnonymousUser

from app.projects.models import Project, ProjectMembership
from app.projects.services.project_team_service import assign_team
from core.permissions.resolver import (
    can_override_member_policy, can_view_project, can_view_team, effective_role,
    is_governance_backstop, is_team_governance_backstop, member_admin_role,
    resolve_permission_root, team_member_admin_role,
)
from core.testing.base import BaseAPITestCase
from core.utils.project_utils import count_explicit_members, get_stale_explicit_members


def fresh(project):
    """Re-fetch so the per-instance team-link cache is rebuilt."""
    return Project.objects.get(pk=project.pk)


class EffectiveRoleTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)

    def test_outsider_has_no_role(self):
        self.assertIsNone(effective_role(self.make_user(), self.project))

    def test_none_project_has_no_role(self):
        self.assertIsNone(effective_role(self.owner, None))

    def test_explicit_membership(self):
        user = self.make_user()
        self.add_project_member(self.project, user, "LEAD")
        self.assertEqual(effective_role(user, self.project), "LEAD")

    def test_creator_is_owner(self):
        self.assertEqual(effective_role(self.owner, self.project), "OWNER")

    def test_team_derived_role_comes_from_the_link_not_the_team_role(self):
        t_owner, member = self.make_user(), self.make_user()
        team = self.make_team(t_owner)
        self.add_team_member(team, member, "VIEWER")  # team-level VIEWER...
        assign_team(project=self.project, team=team, role="MANAGER", is_owning=True, assigned_by=self.owner)
        # ...but the *link* decides the project role - and nobody is written into ProjectMembership.
        self.assertEqual(effective_role(member, fresh(self.project)), "MANAGER")
        self.assertFalse(ProjectMembership.objects.filter(project=self.project, user=member).exists())

    def test_most_permissive_wins_explicit_over_team(self):
        user = self.make_user()
        team = self.make_team(self.make_user())
        self.add_team_member(team, user, "MEMBER")
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.add_project_member(self.project, user, "LEAD")
        self.assertEqual(effective_role(user, fresh(self.project)), "LEAD")

    def test_most_permissive_wins_team_over_explicit(self):
        user = self.make_user()
        team = self.make_team(self.make_user())
        self.add_team_member(team, user, "MEMBER")
        assign_team(project=self.project, team=team, role="MANAGER", is_owning=True, assigned_by=self.owner)
        self.add_project_member(self.project, user, "VIEWER")
        self.assertEqual(effective_role(user, fresh(self.project)), "MANAGER")

    def test_several_teams_highest_link_wins(self):
        user = self.make_user()
        team_a, team_b = self.make_team(self.make_user()), self.make_team(self.make_user())
        self.add_team_member(team_a, user)
        self.add_team_member(team_b, user)
        assign_team(project=self.project, team=team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        assign_team(project=self.project, team=team_b, role="LEAD", is_owning=False, assigned_by=self.owner)
        self.assertEqual(effective_role(user, fresh(self.project)), "LEAD")

    def test_effective_role_never_reaches_owner_through_a_team(self):
        # OWNER is reserved for the explicit creator row; a team link can't carry it.
        user = self.make_user()
        team = self.make_team(self.make_user())
        self.add_team_member(team, user)
        assign_team(project=self.project, team=team, role="MANAGER", is_owning=True, assigned_by=self.owner)
        self.assertNotEqual(effective_role(user, fresh(self.project)), "OWNER")

    def test_soft_deleted_team_stops_granting_access(self):
        user = self.make_user()
        team = self.make_team(self.make_user())
        self.add_team_member(team, user)
        assign_team(project=self.project, team=team, role="MANAGER", is_owning=True, assigned_by=self.owner)
        self.assertEqual(effective_role(user, fresh(self.project)), "MANAGER")
        team.is_deleted = True
        team.save()
        self.assertIsNone(effective_role(user, fresh(self.project)))

    def test_leaving_the_team_removes_derived_access_immediately(self):
        user = self.make_user()
        team = self.make_team(self.make_user())
        membership = self.add_team_member(team, user)
        assign_team(project=self.project, team=team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.owner)
        self.assertEqual(effective_role(user, fresh(self.project)), "CONTRIBUTOR")
        membership.delete()
        self.assertIsNone(effective_role(user, fresh(self.project)))


class GovernanceBackstopTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner = self.make_user()
        self.org = self.make_org(self.org_owner)
        self.creator = self.make_user()
        self.add_org_member(self.org, self.creator, "MANAGER")

    def test_org_owner_is_backstop_without_being_a_project_member(self):
        project = self.make_project(self.creator, org=self.org)
        self.assertTrue(is_governance_backstop(self.org_owner, project))
        self.assertTrue(can_override_member_policy(self.org_owner, project))
        self.assertIsNone(effective_role(self.org_owner, project))  # backstop != operational role

    def test_org_admin_and_member_are_not_backstops(self):
        project = self.make_project(self.creator, org=self.org)
        admin, member = self.make_user(), self.make_user()
        self.add_org_member(self.org, admin, "ADMIN")
        self.add_org_member(self.org, member, "MEMBER")
        self.assertFalse(is_governance_backstop(admin, project))
        self.assertFalse(is_governance_backstop(member, project))

    def test_project_creator_is_not_a_backstop_by_that_fact_alone(self):
        project = self.make_project(self.creator)
        self.assertFalse(is_governance_backstop(self.creator, project))

    def test_owning_team_owner_is_backstop(self):
        t_owner = self.make_user()
        team = self.make_team(t_owner)
        project = self.make_project(self.creator, team=team)
        self.assertTrue(is_governance_backstop(t_owner, fresh(project)))

    def test_owning_team_manager_is_not_backstop(self):
        t_owner, t_mgr = self.make_user(), self.make_user()
        team = self.make_team(t_owner)
        self.add_team_member(team, t_mgr, "MANAGER")
        project = self.make_project(self.creator, team=team)
        self.assertFalse(is_governance_backstop(t_mgr, fresh(project)))

    def test_owner_of_a_non_owning_assigned_team_is_NOT_a_backstop(self):
        """Security: assigning a team as a lowly VIEWER must not hand its owner governance power."""
        owning_owner, other_owner = self.make_user(), self.make_user()
        owning, other = self.make_team(owning_owner), self.make_team(other_owner)
        project = self.make_project(self.creator, team=owning)
        assign_team(project=project, team=other, role="VIEWER", is_owning=False, assigned_by=self.creator)
        project = fresh(project)
        self.assertTrue(is_governance_backstop(owning_owner, project))
        self.assertFalse(is_governance_backstop(other_owner, project))

    def test_unauthenticated_and_none_are_never_backstops(self):
        project = self.make_project(self.creator, org=self.org)
        self.assertFalse(is_governance_backstop(AnonymousUser(), project))
        self.assertFalse(is_governance_backstop(None, project))
        self.assertFalse(is_governance_backstop(self.org_owner, None))

    def test_member_admin_role_gives_backstop_owner_authority(self):
        project = self.make_project(self.creator, org=self.org)
        self.assertEqual(member_admin_role(self.org_owner, project), "OWNER")
        self.assertEqual(member_admin_role(self.creator, project), "OWNER")  # creator is explicit OWNER
        manager = self.make_user()
        self.add_project_member(project, manager, "MANAGER")
        self.assertEqual(member_admin_role(manager, project), "MANAGER")
        self.assertIsNone(member_admin_role(self.make_user(), project))

    def test_team_backstop_is_the_org_owner(self):
        team = self.make_team(self.creator, org=self.org)
        self.assertTrue(is_team_governance_backstop(self.org_owner, team))
        self.assertEqual(team_member_admin_role(self.org_owner, team), "OWNER")
        self.assertFalse(is_team_governance_backstop(self.creator, team))
        self.assertEqual(team_member_admin_role(self.creator, team), "OWNER")  # creator is the team's OWNER row

    def test_standalone_team_has_no_backstop(self):
        team = self.make_team(self.creator)
        self.assertFalse(is_team_governance_backstop(self.org_owner, team))
        self.assertFalse(is_team_governance_backstop(AnonymousUser(), team))


class ViewAccessTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)

    def test_project_visible_to_members_org_members_and_team_members_only(self):
        creator, org_member, outsider, t_member = (self.make_user() for _ in range(4))
        self.add_org_member(self.org, creator, "MANAGER")
        self.add_org_member(self.org, org_member, "VIEWER")
        team = self.make_team(creator, org=self.org)
        self.add_org_member(self.org, t_member, "VIEWER")
        self.add_team_member(team, t_member)
        project = self.make_project(creator, org=self.org, team=team)
        project = fresh(project)
        self.assertTrue(can_view_project(creator, project))
        self.assertTrue(can_view_project(org_member, project))   # org member
        self.assertTrue(can_view_project(t_member, project))     # team-derived
        self.assertFalse(can_view_project(outsider, project))
        self.assertFalse(can_view_project(AnonymousUser(), project))
        self.assertFalse(can_view_project(creator, None))

    def test_standalone_project_hidden_from_strangers(self):
        project = self.make_project(self.owner)
        self.assertFalse(can_view_project(self.make_user(), project))

    def test_team_visible_to_members_and_org_members(self):
        team = self.make_team(self.owner, org=self.org)
        org_member, outsider = self.make_user(), self.make_user()
        self.add_org_member(self.org, org_member, "VIEWER")
        self.assertTrue(can_view_team(self.owner, team))
        self.assertTrue(can_view_team(org_member, team))
        self.assertFalse(can_view_team(outsider, team))
        self.assertFalse(can_view_team(None, team))


class PermissionRootTests(BaseAPITestCase):
    """Item 7: the permission root / billing anchor is the owner of the top-most container."""

    def setUp(self):
        super().setUp()
        self.org_owner, self.creator = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)

    def test_project_in_org_resolves_to_org_owner(self):
        project = self.make_project(self.creator, org=self.org)
        self.assertEqual(resolve_permission_root(project), self.org_owner)

    def test_project_in_org_ignores_its_team(self):
        team_owner = self.make_user()
        team = self.make_team(team_owner, org=self.org)
        project = self.make_project(self.creator, org=self.org, team=team)
        self.assertEqual(resolve_permission_root(fresh(project)), self.org_owner)

    def test_standalone_project_with_team_resolves_to_team_owner(self):
        team_owner = self.make_user()
        team = self.make_team(team_owner)
        project = self.make_project(self.creator, team=team)
        self.assertEqual(resolve_permission_root(fresh(project)), team_owner)

    def test_team_without_explicit_owner_row_falls_back_to_creator(self):
        team_owner = self.make_user()
        team = self.make_team(team_owner)
        team.memberships.all().delete()
        project = self.make_project(self.creator, team=team)
        self.assertEqual(resolve_permission_root(fresh(project)), team_owner)

    def test_fully_standalone_project_resolves_to_creator(self):
        project = self.make_project(self.creator)
        self.assertEqual(resolve_permission_root(project), self.creator)

    def test_team_resolves_to_org_owner_or_own_owner(self):
        in_org = self.make_team(self.creator, org=self.org)
        alone = self.make_team(self.creator)
        self.assertEqual(resolve_permission_root(in_org), self.org_owner)
        self.assertEqual(resolve_permission_root(alone), self.creator)

    def test_organization_resolves_to_itself(self):
        self.assertEqual(resolve_permission_root(self.org), self.org_owner)

    def test_unsupported_entity_raises(self):
        with self.assertRaises(TypeError):
            resolve_permission_root(self.creator)

    def test_reparenting_needs_no_data_migration(self):
        """Item 8: the answer is re-derived from current containers every call."""
        project = self.make_project(self.creator)
        self.assertEqual(resolve_permission_root(project), self.creator)
        project.organization = self.org
        project.save()
        self.assertEqual(resolve_permission_root(project), self.org_owner)


class ExplicitMembershipTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.creator = self.make_user()
        self.t_owner, self.tm1, self.tm2, self.outside = (self.make_user() for _ in range(4))
        self.team = self.make_team(self.t_owner)
        self.add_team_member(self.team, self.tm1)
        self.add_team_member(self.team, self.tm2)
        self.project = self.make_project(self.creator)

    def test_without_teams_every_membership_counts(self):
        self.add_project_member(self.project, self.outside)
        self.assertEqual(count_explicit_members(self.project), 2)  # creator + outside

    def test_a_big_team_costs_zero_slots(self):
        assign_team(project=self.project, team=self.team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.creator)
        self.assertEqual(count_explicit_members(fresh(self.project)), 1)  # only the creator

    def test_members_also_on_an_assigned_team_are_not_double_counted(self):
        self.add_project_member(self.project, self.tm1, "LEAD")
        self.add_project_member(self.project, self.outside, "VIEWER")
        assign_team(project=self.project, team=self.team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.creator)
        # creator + outside; tm1 is covered by the team
        self.assertEqual(count_explicit_members(fresh(self.project)), 2)

    def test_stale_standalone_without_container_is_empty(self):
        self.add_project_member(self.project, self.outside)
        self.assertEqual(get_stale_explicit_members(self.project).count(), 0)

    def test_stale_org_project(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        self.add_org_member(org, self.creator, "MANAGER")
        self.add_org_member(org, self.tm1, "MEMBER")
        project = self.make_project(self.creator, org=org)
        self.add_project_member(project, self.tm1)       # still in the org
        self.add_project_member(project, self.outside)   # never in the org -> stale
        stale_users = {m.user_id for m in get_stale_explicit_members(project)}
        self.assertEqual(stale_users, {self.outside.id})

    def test_creator_is_never_stale(self):
        org = self.make_org(self.make_user())
        project = self.make_project(self.creator, org=org)  # creator was never added to the org
        stale_users = {m.user_id for m in get_stale_explicit_members(project)}
        self.assertNotIn(self.creator.id, stale_users)

    def test_stale_by_team_when_member_left_every_team(self):
        project = self.make_project(self.creator, team=self.team)
        self.add_project_member(project, self.tm1, "CONTRIBUTOR")
        project = fresh(project)
        self.assertEqual(get_stale_explicit_members(project).count(), 0)
        self.team.memberships.filter(user=self.tm1).delete()
        self.assertEqual({m.user_id for m in get_stale_explicit_members(fresh(project))}, {self.tm1.id})
