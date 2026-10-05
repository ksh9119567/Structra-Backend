"""
Role-by-role matrices for every DRF permission class, plus RoleCheckerMixin and
the role-grant guard used by invites.
"""
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory

from app.projects.models import Project
from core.constants.org_constant import ORG_ROLE_HIERARCHY
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ROLE_HIERARCHY
from core.permissions import combined, organization, project, team
from core.permissions.mixins import RoleCheckerMixin
from core.testing.base import BaseAPITestCase
from core.utils.role_utils import ensure_can_grant_role


def request_for(user):
    request = APIRequestFactory().get("/")
    request.user = user
    return request


def allowed(permission_cls, user, obj):
    return bool(permission_cls().has_object_permission(request_for(user), None, obj))


class OrganizationPermissionMatrixTests(BaseAPITestCase):
    EXPECTED = {
        organization.IsOrganizationPart:    {"OWNER", "ADMIN", "MANAGER", "MEMBER", "VIEWER"},
        organization.IsOrganizationMember:  {"OWNER", "ADMIN", "MANAGER", "MEMBER"},
        organization.IsOrganizationManager: {"OWNER", "ADMIN", "MANAGER"},
        organization.IsOrganizationAdmin:   {"OWNER", "ADMIN"},
        organization.IsOrganizationOwner:   {"OWNER"},
    }

    def test_matrix(self):
        owner = self.make_user()
        org = self.make_org(owner)
        users = {"OWNER": owner}
        for role in ("ADMIN", "MANAGER", "MEMBER", "VIEWER"):
            users[role] = self.make_user()
            self.add_org_member(org, users[role], role)
        stranger = self.make_user()
        for perm, roles in self.EXPECTED.items():
            for role, user in users.items():
                self.assertEqual(allowed(perm, user, org), role in roles, f"{perm.__name__} / {role}")
            self.assertFalse(allowed(perm, stranger, org), f"{perm.__name__} / stranger")
            self.assertFalse(allowed(perm, AnonymousUser(), org), f"{perm.__name__} / anonymous")
        self.assertEqual(set(self.EXPECTED[organization.IsOrganizationPart]), set(ORG_ROLE_HIERARCHY))


class TeamPermissionMatrixTests(BaseAPITestCase):
    EXPECTED = {
        team.IsTeamPart:    {"OWNER", "MANAGER", "LEAD", "MEMBER", "VIEWER"},
        team.IsTeamMember:  {"OWNER", "MANAGER", "LEAD", "MEMBER", "VIEWER"},
        team.IsTeamManager: {"OWNER", "MANAGER"},
        team.IsTeamOwner:   {"OWNER"},
    }

    def test_matrix(self):
        owner = self.make_user()
        t = self.make_team(owner)
        users = {"OWNER": owner}
        for role in ("MANAGER", "LEAD", "MEMBER", "VIEWER"):
            users[role] = self.make_user()
            self.add_team_member(t, users[role], role)
        stranger = self.make_user()
        for perm, roles in self.EXPECTED.items():
            for role, user in users.items():
                self.assertEqual(allowed(perm, user, t), role in roles, f"{perm.__name__} / {role}")
            self.assertFalse(allowed(perm, stranger, t), f"{perm.__name__} / stranger")
            self.assertFalse(allowed(perm, AnonymousUser(), t), f"{perm.__name__} / anonymous")
        self.assertEqual(set(self.EXPECTED[team.IsTeamPart]), set(TEAM_ROLE_HIERARCHY))


class ProjectPermissionMatrixTests(BaseAPITestCase):
    EXPECTED = {
        project.IsProjectMember:      {"OWNER", "MANAGER", "LEAD", "CONTRIBUTOR", "VIEWER", "GUEST"},
        project.IsProjectContributor: {"OWNER", "MANAGER", "LEAD", "CONTRIBUTOR"},
        project.IsProjectLead:        {"OWNER", "MANAGER", "LEAD"},
        project.IsProjectManager:     {"OWNER", "MANAGER"},
        project.IsProjectOwner:       {"OWNER"},
    }

    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)
        self.users = {"OWNER": self.owner}
        for role in ("MANAGER", "LEAD", "CONTRIBUTOR", "VIEWER", "GUEST"):
            self.users[role] = self.make_user()
            self.add_project_member(self.project, self.users[role], role)

    def test_matrix_for_explicit_members(self):
        stranger = self.make_user()
        for perm, roles in self.EXPECTED.items():
            for role, user in self.users.items():
                self.assertEqual(allowed(perm, user, self.project), role in roles, f"{perm.__name__} / {role}")
            self.assertFalse(allowed(perm, stranger, self.project), f"{perm.__name__} / stranger")
            self.assertFalse(allowed(perm, AnonymousUser(), self.project), f"{perm.__name__} / anonymous")
        self.assertEqual(set(self.EXPECTED[project.IsProjectMember]), set(PROJECT_ROLE_HIERARCHY))

    def test_team_derived_participants_are_judged_by_the_link_role(self):
        t = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(t, member, "VIEWER")       # team-level role is irrelevant
        from app.projects.services.project_team_service import assign_team
        assign_team(project=self.project, team=t, role="MANAGER", is_owning=True, assigned_by=self.owner)
        fresh = Project.objects.get(pk=self.project.pk)
        self.assertTrue(allowed(project.IsProjectManager, member, fresh))
        self.assertFalse(allowed(project.IsProjectOwner, member, fresh))


class CombinedPermissionTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.creator = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.creator, "MANAGER")
        self.team = self.make_team(self.creator, org=self.org)
        self.project = self.make_project(self.creator, org=self.org)
        self.admin = self.make_user()
        self.add_org_member(self.org, self.admin, "ADMIN")

    def test_org_owner_or_project_role_classes(self):
        lead, contributor = self.make_user(), self.make_user()
        self.add_project_member(self.project, lead, "LEAD")
        self.add_project_member(self.project, contributor, "CONTRIBUTOR")
        cases = {
            combined.IsOrgOwnerOrProjectLead:    {self.org_owner: True, self.creator: True, lead: True,
                                                  contributor: False, self.admin: False},
            combined.IsOrgOwnerOrProjectManager: {self.org_owner: True, self.creator: True, lead: False,
                                                  contributor: False, self.admin: False},
            combined.IsOrgOwnerOrProjectOwner:   {self.org_owner: True, self.creator: True, lead: False,
                                                  contributor: False, self.admin: False},
        }
        for perm, expectations in cases.items():
            for user, expected in expectations.items():
                self.assertEqual(allowed(perm, user, self.project), expected, f"{perm.__name__} / {user.email}")

    def test_org_owner_or_team_role_classes(self):
        manager, member = self.make_user(), self.make_user()
        self.add_team_member(self.team, manager, "MANAGER")
        self.add_team_member(self.team, member, "MEMBER")
        self.assertTrue(allowed(combined.IsOrgOwnerOrTeamOwner, self.org_owner, self.team))
        self.assertTrue(allowed(combined.IsOrgOwnerOrTeamOwner, self.creator, self.team))
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamOwner, manager, self.team))
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamOwner, self.admin, self.team))
        self.assertTrue(allowed(combined.IsOrgOwnerOrTeamManager, self.org_owner, self.team))
        self.assertTrue(allowed(combined.IsOrgOwnerOrTeamManager, manager, self.team))
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamManager, member, self.team))

    def test_standalone_team_has_no_org_owner_shortcut(self):
        standalone = self.make_team(self.creator)
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamOwner, self.org_owner, standalone))
        self.assertTrue(allowed(combined.IsOrgOwnerOrTeamOwner, self.creator, standalone))

    def test_missing_team_is_denied_not_crashed(self):
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamOwner, self.org_owner, None))
        self.assertFalse(allowed(combined.IsOrgOwnerOrTeamManager, self.org_owner, None))

    def test_anonymous_is_always_denied(self):
        for perm in (combined.IsOrgOwnerOrProjectLead, combined.IsOrgOwnerOrProjectManager, combined.IsOrgOwnerOrProjectOwner):
            self.assertFalse(allowed(perm, AnonymousUser(), self.project))
        for perm in (combined.IsOrgOwnerOrTeamOwner, combined.IsOrgOwnerOrTeamManager):
            self.assertFalse(allowed(perm, AnonymousUser(), self.team))


class RoleCheckerMixinTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.check = RoleCheckerMixin().has_minimum_role

    def test_comparison(self):
        self.assertTrue(self.check("MANAGER", "LEAD", PROJECT_ROLE_HIERARCHY))
        self.assertTrue(self.check("LEAD", "LEAD", PROJECT_ROLE_HIERARCHY))
        self.assertFalse(self.check("VIEWER", "LEAD", PROJECT_ROLE_HIERARCHY))

    def test_missing_or_unknown_roles_never_pass(self):
        self.assertFalse(self.check(None, "LEAD", PROJECT_ROLE_HIERARCHY))
        self.assertFalse(self.check("LEAD", None, PROJECT_ROLE_HIERARCHY))
        self.assertFalse(self.check("", "LEAD", PROJECT_ROLE_HIERARCHY))
        self.assertFalse(self.check("EMPEROR", "LEAD", PROJECT_ROLE_HIERARCHY))
        self.assertFalse(self.check("LEAD", "EMPEROR", PROJECT_ROLE_HIERARCHY))

    def test_a_role_from_another_scope_is_not_known(self):
        # GUEST exists only in the project scope
        self.assertFalse(self.check("GUEST", "VIEWER", ORG_ROLE_HIERARCHY))


class EnsureCanGrantRoleTests(BaseAPITestCase):
    H = PROJECT_ROLE_HIERARCHY

    def grant(self, role, granter):
        return ensure_can_grant_role(role=role, granter_role=granter, hierarchy=self.H)

    def test_owner_is_never_grantable(self):
        for granter in ("OWNER", "MANAGER", "LEAD"):
            with self.assertRaises(ValidationError):
                self.grant("OWNER", granter)

    def test_owner_may_grant_every_other_role(self):
        for role in ("MANAGER", "LEAD", "CONTRIBUTOR", "VIEWER", "GUEST"):
            self.grant(role, "OWNER")

    def test_others_may_only_grant_strictly_below_themselves(self):
        self.grant("LEAD", "MANAGER")
        self.grant("GUEST", "LEAD")
        for role in ("MANAGER", "LEAD"):
            with self.assertRaises(ValidationError):
                self.grant(role, "LEAD")
        with self.assertRaises(ValidationError):
            self.grant("MANAGER", "MANAGER")

    def test_no_role_means_no_authority(self):
        with self.assertRaises(PermissionDenied):
            self.grant("VIEWER", None)
        with self.assertRaises(PermissionDenied):
            self.grant("VIEWER", "NOT-A-ROLE")
