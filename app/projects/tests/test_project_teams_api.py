"""
Multi-team support (Phase C): list / assign / update-role / unassign endpoints
and how team-derived access behaves through the API.
"""
from datetime import timedelta

from django.utils import timezone

from app.projects.models import ProjectMembership, ProjectTeam
from app.projects.services.project_team_service import assign_team
from .helpers import ProjectAPITestCase, purl


class TeamLinkTestBase(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)
        self.team_a = self.make_team(self.owner, name="A")
        self.team_b = self.make_team(self.owner, name="B")
        self.team_c = self.make_team(self.owner, name="C")

    def assign(self, team, role="CONTRIBUTOR", is_owning=None, actor=None, project=None):
        data = {"team_id": str(team.id), "role": role}
        if is_owning is not None:
            data["is_owning"] = is_owning
        return self.post(actor or self.owner, "assign-team", data, project_id=(project or self.project).id)

    def link(self, team, project=None):
        return ProjectTeam.objects.get(project=project or self.project, team=team)

    def owning_team(self, project=None):
        link = ProjectTeam.objects.filter(project=project or self.project, is_owning=True).first()
        return link.team if link else None


class ListProjectTeamsTests(TeamLinkTestBase):
    def test_owning_team_is_listed_first_with_details(self):
        assign_team(project=self.project, team=self.team_a, role="VIEWER", is_owning=False, assigned_by=self.owner)
        assign_team(project=self.project, team=self.team_b, role="LEAD", is_owning=True, assigned_by=self.owner)
        resp = self.get(self.owner, "get-project-teams", project_id=self.project.id)
        self.assertOK(resp)
        data = resp.data["data"]
        self.assertEqual([d["team_name"] for d in data], ["B", "A"])
        self.assertEqual((data[0]["role"], data[0]["is_owning"]), ("LEAD", True))
        self.assertEqual(data[0]["assigned_by_email"], self.owner.email)

    def test_empty_project(self):
        self.assertEqual(self.get(self.owner, "get-project-teams", project_id=self.project.id).data["data"], [])

    def test_any_member_can_see_but_outsiders_cannot(self):
        viewer = self.make_user()
        self.add_project_member(self.project, viewer, "VIEWER")
        self.assertOK(self.get(viewer, "get-project-teams", project_id=self.project.id))
        self.assertDenied(self.get(self.make_user(), "get-project-teams", project_id=self.project.id))


class AssignTeamTests(TeamLinkTestBase):
    def test_first_team_is_always_owning_even_if_not_requested(self):
        resp = self.assign(self.team_a, is_owning=False)
        self.assertOK(resp)
        self.assertTrue(resp.data["data"]["is_owning"])
        self.assertEqual(self.owning_team(), self.team_a)

    def test_later_teams_are_not_owning_by_default(self):
        self.assign(self.team_a)
        resp = self.assign(self.team_b, role="VIEWER")
        self.assertOK(resp)
        self.assertFalse(resp.data["data"]["is_owning"])
        self.assertEqual(self.owning_team(), self.team_a)

    def test_flagging_a_new_team_as_owning_demotes_the_previous_one(self):
        self.assign(self.team_a)
        self.assertOK(self.assign(self.team_b, is_owning=True))
        self.assertEqual(self.owning_team(), self.team_b)
        self.assertFalse(self.link(self.team_a).is_owning)
        self.assertEqual(ProjectTeam.objects.filter(project=self.project, is_owning=True).count(), 1)

    def test_assigning_an_already_linked_team_updates_its_role(self):
        self.assign(self.team_a, role="VIEWER")
        self.assertOK(self.assign(self.team_a, role="MANAGER"))
        self.assertEqual(self.project.team_links.count(), 1)
        self.assertEqual(self.link(self.team_a).role, "MANAGER")

    def test_assigned_by_is_recorded(self):
        self.assign(self.team_a)
        self.assertEqual(self.link(self.team_a).assigned_by, self.owner)

    def test_the_link_role_cannot_be_owner_or_guest(self):
        for bad in ("OWNER", "GUEST", "BOSS"):
            self.assertOK(self.assign(self.team_a, role=bad), 400)
        self.assertEqual(self.project.team_links.count(), 0)

    def test_required_fields(self):
        self.assertOK(self.post(self.owner, "assign-team", {"role": "VIEWER"}, project_id=self.project.id), 400)
        self.assertOK(self.post(self.owner, "assign-team", {"team_id": str(self.team_a.id)}, project_id=self.project.id), 400)

    def test_unknown_and_deleted_teams_are_rejected(self):
        resp = self.post(self.owner, "assign-team",
                         {"team_id": "00000000-0000-0000-0000-000000000000", "role": "VIEWER"}, project_id=self.project.id)
        self.assertOK(resp, 400)
        self.team_a.is_deleted = True
        self.team_a.save()
        self.assertOK(self.assign(self.team_a), 400)

    def test_team_from_another_org_is_rejected(self):
        org1, org2 = self.make_org(self.owner), self.make_org(self.owner)
        project = self.make_project(self.owner, org=org1)
        foreign = self.make_team(self.owner, org=org2)
        self.assertOK(self.assign(foreign, project=project), 400)
        same_org = self.make_team(self.owner, org=org1)
        self.assertOK(self.assign(same_org, project=project))

    def test_caller_needs_authority_over_the_team_being_assigned(self):
        not_mine = self.make_team(self.make_user())
        self.assertOK(self.assign(not_mine), 400)            # not on that team at all
        self.add_team_member(not_mine, self.owner, "MEMBER")
        self.assertOK(self.assign(not_mine), 400)            # too junior (min role MANAGER)
        not_mine.memberships.filter(user=self.owner).update(role="MANAGER")
        self.assertOK(self.assign(not_mine))

    def test_project_contributors_and_outsiders_cannot_assign(self):
        contributor = self.make_user()
        self.add_project_member(self.project, contributor, "CONTRIBUTOR")
        self.assertDenied(self.assign(self.team_a, actor=contributor))
        self.assertDenied(self.assign(self.team_a, actor=self.make_user()))

    def test_requires_authentication(self):
        resp = self.anon().post(purl("assign-team", project_id=self.project.id),
                                {"team_id": str(self.team_a.id), "role": "VIEWER"}, format="json")
        self.assertDenied(resp, 401)


class UpdateTeamRoleTests(TeamLinkTestBase):
    def setUp(self):
        super().setUp()
        assign_team(project=self.project, team=self.team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        assign_team(project=self.project, team=self.team_b, role="VIEWER", is_owning=False, assigned_by=self.owner)

    def update(self, team, actor=None, **data):
        return self.put(actor or self.owner, "update-team-role", {"team_id": str(team.id), **data}, project_id=self.project.id)

    def test_change_the_role(self):
        self.assertOK(self.update(self.team_b, role="LEAD"))
        self.assertEqual(self.link(self.team_b).role, "LEAD")

    def test_promoting_to_owning_swaps_the_flag(self):
        self.assertOK(self.update(self.team_b, is_owning=True))
        self.assertEqual(self.owning_team(), self.team_b)
        self.assertFalse(self.link(self.team_a).is_owning)

    def test_cannot_unflag_the_only_owning_team(self):
        resp = self.update(self.team_a, is_owning=False)
        self.assertOK(resp, 400)
        self.assertEqual(self.owning_team(), self.team_a)

    def test_unflagging_a_non_owning_team_is_a_no_op(self):
        self.assertOK(self.update(self.team_b, is_owning=False))
        self.assertEqual(self.owning_team(), self.team_a)

    def test_team_not_assigned_is_404(self):
        self.assertOK(self.update(self.team_c, role="LEAD"), 404)

    def test_needs_something_to_update_and_a_valid_role(self):
        self.assertOK(self.update(self.team_b), 400)
        self.assertOK(self.update(self.team_b, role="OWNER"), 400)
        self.assertOK(self.update(self.team_b, role="GUEST"), 400)

    def test_contributors_cannot_update_links(self):
        contributor = self.make_user()
        self.add_project_member(self.project, contributor, "CONTRIBUTOR")
        self.assertDenied(self.update(self.team_b, actor=contributor, role="LEAD"))


class UnassignTeamTests(TeamLinkTestBase):
    def setUp(self):
        super().setUp()
        base = timezone.now()
        for offset, (team, owning) in enumerate([(self.team_a, True), (self.team_b, False), (self.team_c, False)]):
            assign_team(project=self.project, team=team, role="CONTRIBUTOR", is_owning=owning, assigned_by=self.owner)
            # pin assignment order so "earliest remaining" is deterministic
            ProjectTeam.objects.filter(project=self.project, team=team).update(created_at=base + timedelta(seconds=offset))

    def unassign(self, team, actor=None, project=None):
        return self.delete(actor or self.owner, "unassign-team", {"team_id": str(team.id)},
                           project_id=(project or self.project).id)

    def test_unassigning_a_non_owning_team_keeps_the_owner(self):
        self.assertOK(self.unassign(self.team_c))
        self.assertEqual(self.owning_team(), self.team_a)
        self.assertEqual(self.project.team_links.count(), 2)

    def test_unassigning_the_owning_team_promotes_the_earliest_remaining(self):
        self.assertOK(self.unassign(self.team_a))
        self.assertEqual(self.owning_team(), self.team_b)
        self.assertEqual(ProjectTeam.objects.filter(project=self.project, is_owning=True).count(), 1)

    def test_unassigning_the_last_team_leaves_no_owning_team(self):
        for team in (self.team_c, self.team_b, self.team_a):
            self.assertOK(self.unassign(team))
        self.assertEqual(self.project.team_links.count(), 0)
        self.assertIsNone(self.owning_team())

    def test_team_not_assigned_and_bad_input(self):
        other = self.make_team(self.owner)
        self.assertOK(self.unassign(other), 404)
        self.assertOK(self.delete(self.owner, "unassign-team", {}, project_id=self.project.id), 400)
        self.assertOK(self.delete(self.owner, "unassign-team", {"team_id": "00000000-0000-0000-0000-000000000000"},
                                  project_id=self.project.id), 404)

    def test_team_members_lose_access_immediately(self):
        member = self.make_user()
        self.add_team_member(self.team_a, member)
        self.assertOK(self.get(member, "get-project-details", project_id=self.project.id))
        self.assertOK(self.unassign(self.team_a))
        # still assigned? team_b / team_c do not contain the member
        self.assertDenied(self.get(member, "get-project-details", project_id=self.project.id))

    def test_contributors_cannot_unassign(self):
        contributor = self.make_user()
        self.add_project_member(self.project, contributor, "CONTRIBUTOR")
        self.assertDenied(self.unassign(self.team_b, actor=contributor))


class TeamDerivedAccessThroughTheApiTests(TeamLinkTestBase):
    def setUp(self):
        super().setUp()
        self.member = self.make_user()
        self.add_team_member(self.team_a, self.member, "MEMBER")

    def link_role(self, role):
        assign_team(project=self.project, team=self.team_a, role=role, is_owning=True, assigned_by=self.owner)

    def test_viewer_link_gives_read_access_only(self):
        self.link_role("VIEWER")
        self.assertOK(self.get(self.member, "get-project-details", project_id=self.project.id))
        self.assertOK(self.get(self.member, "get-project-members", project_id=self.project.id))
        self.assertOK(self.get(self.member, "get-project-teams", project_id=self.project.id))
        self.assertDenied(self.put(self.member, "update-project", {"project_id": str(self.project.id), "name": "x"}))
        self.assertDenied(self.post(self.member, "send-invite", {"email": self.make_user().email}, project_id=self.project.id))
        self.assertDenied(self.get(self.member, "get-stale-members", project_id=self.project.id))

    def test_manager_link_unlocks_manager_endpoints(self):
        self.link_role("MANAGER")
        self.assertOK(self.get(self.member, "get-stale-members", project_id=self.project.id))
        self.assertDenied(self.put(self.member, "update-project", {"project_id": str(self.project.id), "name": "x"}))  # still not OWNER

    def test_team_members_are_never_written_into_the_member_list(self):
        self.link_role("MANAGER")
        self.assertFalse(ProjectMembership.objects.filter(project=self.project, user=self.member).exists())
        resp = self.get(self.owner, "get-project-members", project_id=self.project.id)
        self.assertEqual(resp.data["count"], 1)

    def test_changing_the_link_role_changes_everyones_access_at_once(self):
        self.link_role("VIEWER")
        self.assertDenied(self.get(self.member, "get-stale-members", project_id=self.project.id))
        self.assertOK(self.put(self.owner, "update-team-role", {"team_id": str(self.team_a.id), "role": "MANAGER"},
                               project_id=self.project.id))
        self.assertOK(self.get(self.member, "get-stale-members", project_id=self.project.id))

    def test_leaving_the_team_removes_access(self):
        self.link_role("CONTRIBUTOR")
        self.assertOK(self.get(self.member, "get-project-details", project_id=self.project.id))
        self.team_a.memberships.filter(user=self.member).delete()
        self.assertDenied(self.get(self.member, "get-project-details", project_id=self.project.id))

    def test_a_member_of_two_assigned_teams_gets_the_higher_link_role(self):
        self.add_team_member(self.team_b, self.member, "MEMBER")
        assign_team(project=self.project, team=self.team_a, role="VIEWER", is_owning=True, assigned_by=self.owner)
        assign_team(project=self.project, team=self.team_b, role="MANAGER", is_owning=False, assigned_by=self.owner)
        self.assertOK(self.get(self.member, "get-stale-members", project_id=self.project.id))
