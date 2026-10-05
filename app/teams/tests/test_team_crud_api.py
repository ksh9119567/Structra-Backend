"""
Team CRUD endpoints: create, list, retrieve, update, delete, transfer-owner and
the org team listing.
"""
from unittest import mock

from app.projects.models import ProjectTeam
from app.projects.services.project_team_service import assign_team
from app.teams.models import Team, TeamMembership
from .helpers import TeamAPITestCase, ids, results, turl


class TeamCreateTests(TeamAPITestCase):
    def test_creates_standalone_team_with_creator_as_owner(self):
        user = self.make_user()
        resp = self.post(user, "create-team", {"name": "Core", "description": "d"})
        self.assertOK(resp, 201)
        team = Team.objects.get(id=resp.data["data"]["id"])
        self.assertEqual((team.name, team.created_by), ("Core", user))
        self.assertEqual(TeamMembership.objects.get(team=team, user=user).role, "OWNER")
        self.assertTrue(hasattr(team, "settings"))
        self.assertIsNone(team.organization)

    def test_requires_authentication_and_a_name(self):
        self.assertDenied(self.anon().post(turl("create-team"), {"name": "x"}, format="json"), 401)
        self.assertOK(self.post(self.make_user(), "create-team", {"description": "no name"}), 400)

    def test_org_owner_creates_a_team_in_the_org(self):
        owner = self.make_user()
        org = self.make_org(owner)
        resp = self.post(owner, "create-team", {"name": "T", "organization_id": str(org.id)})
        self.assertOK(resp, 201)
        self.assertEqual(Team.objects.get(id=resp.data["data"]["id"]).organization, org)

    def test_plain_org_member_cannot_create_by_default(self):
        org = self.make_org(self.make_user())
        member = self.make_user()
        self.add_org_member(org, member, "MEMBER")
        self.assertOK(self.post(member, "create-team", {"name": "T", "organization_id": str(org.id)}), 400)

    def test_member_below_the_min_role_cannot_create_even_when_allowed(self):
        org = self.make_org(self.make_user(), allow_team_creation=True)
        member = self.make_user()
        self.add_org_member(org, member, "MEMBER")
        self.assertOK(self.post(member, "create-team", {"name": "T", "organization_id": str(org.id)}), 400)

    def test_admin_can_create_when_allowed(self):
        org = self.make_org(self.make_user(), allow_team_creation=True)
        admin = self.make_user()
        self.add_org_member(org, admin, "ADMIN")
        self.assertOK(self.post(admin, "create-team", {"name": "T", "organization_id": str(org.id)}), 201)

    def test_non_member_of_the_org_is_refused_not_crashed(self):
        org = self.make_org(self.make_user())
        self.assertOK(self.post(self.make_user(), "create-team", {"name": "T", "organization_id": str(org.id)}), 404)

    def test_unknown_org_is_404(self):
        resp = self.post(self.make_user(), "create-team",
                         {"name": "T", "organization_id": "00000000-0000-0000-0000-000000000000"})
        self.assertOK(resp, 404)

    def test_org_team_quota_is_enforced_and_deleted_teams_free_a_slot(self):
        owner = self.make_user()
        org = self.make_org(owner, max_teams=1)
        first = self.post(owner, "create-team", {"name": "one", "organization_id": str(org.id)})
        self.assertOK(first, 201)
        self.assertOK(self.post(owner, "create-team", {"name": "two", "organization_id": str(org.id)}), 400)
        self.assertOK(self.delete(owner, "delete-team", {"team_id": first.data["data"]["id"]}))
        self.assertOK(self.post(owner, "create-team", {"name": "three", "organization_id": str(org.id)}), 201)

    def test_quota_blocks_even_when_already_over_the_limit(self):
        owner = self.make_user()
        org = self.make_org(owner, max_teams=1)
        self.make_team(owner, org=org)
        self.make_team(owner, org=org)
        self.assertOK(self.post(owner, "create-team", {"name": "x", "organization_id": str(org.id)}), 400)

    def test_a_failure_while_writing_the_owner_membership_leaves_no_orphan_team(self):
        owner = self.make_user()
        client = self.client_for(owner)
        with mock.patch("app.teams.api.v1.serializers.TeamMembership.objects.create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                client.post(turl("create-team"), {"name": "T"}, format="json")
        self.assertEqual(Team.objects.count(), 0)


class TeamListAndRetrieveTests(TeamAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.owner = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.owner, "MANAGER")
        self.team = self.make_team(self.owner, org=self.org)

    def test_list_returns_only_my_live_teams(self):
        mine_standalone = self.make_team(self.owner)
        gone = self.make_team(self.owner)
        gone.is_deleted = True
        gone.save()
        self.make_team(self.make_user())
        resp = self.get(self.owner, "get-user-teams")
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(self.team.id), str(mine_standalone.id)})

    def test_list_search(self):
        self.make_team(self.owner, name="Zebra")
        self.assertEqual(len(results(self.get(self.owner, "get-user-teams", search="zeb"))), 1)

    def test_member_can_retrieve(self):
        resp = self.get(self.owner, "get-team-details", team_id=self.team.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["name"], self.team.name)
        self.assertEqual(resp.data["data"]["organization_name"], self.org.name)
        self.assertEqual(resp.data["data"]["member_count"], 1)

    def test_org_member_who_is_not_on_the_team_can_retrieve(self):
        """REGRESSION: used to 404 because the org fallback was never reached."""
        viewer = self.make_user()
        self.add_org_member(self.org, viewer, "VIEWER")
        self.assertOK(self.get(viewer, "get-team-details", team_id=self.team.id))
        self.assertOK(self.get(viewer, "get-team-members", team_id=self.team.id))

    def test_outsider_is_403_for_org_and_standalone_teams(self):
        stranger = self.make_user()
        self.assertDenied(self.get(stranger, "get-team-details", team_id=self.team.id))
        standalone = self.make_team(self.owner)
        self.assertDenied(self.get(stranger, "get-team-details", team_id=standalone.id))
        self.assertDenied(self.get(stranger, "get-team-members", team_id=standalone.id))

    def test_unknown_malformed_missing_and_deleted_ids(self):
        self.assertOK(self.get(self.owner, "get-team-details", team_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-team-details", team_id="not-a-uuid"), 404)
        self.assertOK(self.get(self.owner, "get-team-details"), 400)
        self.team.is_deleted = True
        self.team.save()
        self.assertOK(self.get(self.owner, "get-team-details", team_id=self.team.id), 404)

    def test_org_teams_listing(self):
        self.make_team(self.owner)  # standalone - not in the org
        dead = self.make_team(self.owner, org=self.org)
        dead.is_deleted = True
        dead.save()
        resp = self.get(self.owner, "get-org-teams", org_id=self.org.id)
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(self.team.id)})

    def test_org_teams_listing_is_for_org_members_only(self):
        self.assertDenied(self.get(self.make_user(), "get-org-teams", org_id=self.org.id))
        self.assertOK(self.get(self.owner, "get-org-teams", org_id="00000000-0000-0000-0000-000000000000"), 404)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(turl("get-user-teams")), 401)
        self.assertDenied(self.anon().get(turl("get-team-details", team_id=self.team.id)), 401)


class TeamUpdateTests(TeamAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.owner = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.owner, "MANAGER")
        self.team = self.make_team(self.owner, org=self.org)

    def update(self, user, **data):
        return self.put(user, "update-team", {"team_id": str(self.team.id), **data})

    def test_owner_updates(self):
        self.assertOK(self.update(self.owner, name="New", description="d"))
        self.team.refresh_from_db()
        self.assertEqual((self.team.name, self.team.description), ("New", "d"))

    def test_org_owner_can_update(self):
        self.assertOK(self.update(self.org_owner, name="By org owner"))

    def test_manager_member_and_outsider_cannot(self):
        manager, member = self.make_user(), self.make_user()
        self.add_team_member(self.team, manager, "MANAGER")
        self.add_team_member(self.team, member, "MEMBER")
        for user in (manager, member, self.make_user()):
            self.assertDenied(self.update(user, name="x"))

    def test_unknown_and_missing_team(self):
        self.assertOK(self.put(self.owner, "update-team", {"team_id": "00000000-0000-0000-0000-000000000000"}), 404)
        self.assertOK(self.put(self.owner, "update-team", {"name": "x"}), 400)


class TeamDeleteTests(TeamAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.creator = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.creator, "MANAGER")
        self.team = self.make_team(self.creator, org=self.org)

    def remove(self, user, team=None):
        return self.delete(user, "delete-team", {"team_id": str((team or self.team).id)})

    def test_creator_deletes_softly(self):
        self.assertOK(self.remove(self.creator))
        self.team.refresh_from_db()
        self.assertTrue(self.team.is_deleted)
        self.assertEqual(ids(self.get(self.creator, "get-user-teams")), set())
        self.assertOK(self.get(self.creator, "get-team-details", team_id=self.team.id), 404)

    def test_deleting_twice_is_404(self):
        self.assertOK(self.remove(self.creator))
        self.assertOK(self.remove(self.creator), 404)

    def test_org_owner_backstop_can_delete_a_team_they_are_not_in(self):
        """REGRESSION: the permission class admitted the org owner but delete_team() rejected them."""
        self.assertFalse(TeamMembership.objects.filter(team=self.team, user=self.org_owner).exists())
        self.assertOK(self.remove(self.org_owner))
        self.team.refresh_from_db()
        self.assertTrue(self.team.is_deleted)

    def test_manager_member_org_admin_and_stranger_cannot_delete(self):
        manager, admin = self.make_user(), self.make_user()
        self.add_team_member(self.team, manager, "MANAGER")
        self.add_org_member(self.org, admin, "ADMIN")
        for user in (manager, admin, self.make_user()):
            self.assertDenied(self.remove(user))
        self.team.refresh_from_db()
        self.assertFalse(self.team.is_deleted)

    def test_a_standalone_team_has_no_backstop(self):
        standalone = self.make_team(self.creator)
        self.assertDenied(self.remove(self.org_owner, standalone))

    def test_deleting_a_team_revokes_the_project_access_it_granted(self):
        member = self.make_user()
        self.add_team_member(self.team, member)
        project = self.make_project(self.creator, org=self.org, team=self.team)
        projects = f"/api/v1/projects/get-project-details/?project_id={project.id}"
        self.assertOK(self.client_for(member).get(projects))
        self.assertOK(self.remove(self.creator))
        self.assertEqual(ProjectTeam.objects.filter(team=self.team).count(), 0)
        # member is not in the org either, so access is truly gone
        self.assertDenied(self.client_for(member).get(projects))

    def test_deleting_the_owning_team_promotes_another_assigned_team(self):
        other = self.make_team(self.creator, org=self.org)
        project = self.make_project(self.creator, org=self.org, team=self.team)
        assign_team(project=project, team=other, role="VIEWER", is_owning=False, assigned_by=self.creator)
        self.assertOK(self.remove(self.creator))
        link = ProjectTeam.objects.get(project=project)
        self.assertEqual((link.team, link.is_owning), (other, True))

    def test_requires_authentication(self):
        resp = self.anon().delete(turl("delete-team"), {"team_id": str(self.team.id)}, format="json")
        self.assertDenied(resp, 401)


class TeamTransferOwnerTests(TeamAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.creator, self.heir = (self.make_user() for _ in range(3))
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.creator, "MANAGER")
        self.add_org_member(self.org, self.heir, "MEMBER")
        self.team = self.make_team(self.creator, org=self.org)
        self.add_team_member(self.team, self.heir, "MANAGER")

    def transfer(self, user, email, team=None):
        return self.put(user, "transfer-owner", {"email": email}, team_id=(team or self.team).id)

    def roles(self):
        return {m.user_id: m.role for m in self.team.memberships.all()}

    def test_creator_hands_over(self):
        self.assertOK(self.transfer(self.creator, self.heir.email))
        self.team.refresh_from_db()
        self.assertEqual(self.team.created_by, self.heir)
        self.assertEqual(self.roles()[self.heir.id], "OWNER")
        self.assertEqual(self.roles()[self.creator.id], "MANAGER")

    def test_org_owner_backstop_can_transfer(self):
        """REGRESSION: transfer_team_ownership() rejected the org owner on every code path."""
        self.assertOK(self.transfer(self.org_owner, self.heir.email))
        self.team.refresh_from_db()
        self.assertEqual(self.team.created_by, self.heir)

    def test_manager_and_stranger_cannot(self):
        self.assertDenied(self.transfer(self.heir, self.heir.email))
        self.assertDenied(self.transfer(self.make_user(), self.heir.email))

    def test_validation(self):
        self.assertOK(self.transfer(self.creator, self.creator.email), 400)               # already the creator
        self.assertOK(self.transfer(self.creator, self.make_user().email), 400)           # not an org member
        in_org_not_team = self.make_user()
        self.add_org_member(self.org, in_org_not_team, "MEMBER")
        self.assertOK(self.transfer(self.creator, in_org_not_team.email), 400)            # not a team member
        self.assertOK(self.transfer(self.creator, "ghost@example.com"), 404)

    def test_standalone_team_only_the_creator_may_transfer(self):
        team = self.make_team(self.creator)
        self.add_team_member(team, self.heir, "MANAGER")
        self.assertDenied(self.transfer(self.org_owner, self.heir.email, team))
        self.assertOK(self.transfer(self.creator, self.heir.email, team))
