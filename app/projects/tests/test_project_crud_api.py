"""
Project CRUD endpoints: create, list, retrieve, update, delete, transfer-owner,
and the org / team project listings.
"""
from unittest import mock

from app.projects.models import Project, ProjectMembership, ProjectTeam
from app.projects.services.project_team_service import assign_team
from .helpers import ProjectAPITestCase, ids, purl, results


class ProjectCreateTests(ProjectAPITestCase):
    def test_creates_standalone_project_with_creator_as_owner(self):
        user = self.make_user()
        resp = self.post(user, "create-project", {"name": "Alpha", "description": "first"})
        self.assertOK(resp, 201)
        project = Project.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(project.name, "Alpha")
        self.assertEqual(project.created_by, user)
        self.assertEqual(ProjectMembership.objects.get(project=project, user=user).role, "OWNER")
        self.assertTrue(hasattr(project, "settings"))
        self.assertIsNone(project.organization)
        self.assertIsNone(project.team)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().post(purl("create-project"), {"name": "x"}, format="json"), 401)

    def test_name_is_required(self):
        self.assertOK(self.post(self.make_user(), "create-project", {"description": "no name"}), 400)

    def test_null_organization_and_team_ids_mean_standalone(self):
        resp = self.post(self.make_user(), "create-project", {"name": "P", "organization_id": None, "team_id": None})
        self.assertOK(resp, 201)

    # ---- inside an organization ----
    def test_org_owner_can_create_in_org(self):
        owner = self.make_user()
        org = self.make_org(owner)
        resp = self.post(owner, "create-project", {"name": "P", "organization_id": str(org.id)})
        self.assertOK(resp, 201)
        self.assertEqual(Project.objects.get(id=resp.data["data"]["id"]).organization, org)

    def test_plain_org_member_cannot_create_by_default(self):
        org = self.make_org(self.make_user())
        member = self.make_user()
        self.add_org_member(org, member, "MEMBER")
        resp = self.post(member, "create-project", {"name": "P", "organization_id": str(org.id)})
        self.assertOK(resp, 400)

    def test_member_below_the_configured_min_role_cannot_create_even_if_allowed(self):
        org = self.make_org(self.make_user(), allow_project_creation=True)  # min role stays ADMIN
        member = self.make_user()
        self.add_org_member(org, member, "MEMBER")
        self.assertOK(self.post(member, "create-project", {"name": "P", "organization_id": str(org.id)}), 400)

    def test_admin_can_create_when_the_org_allows_it(self):
        org = self.make_org(self.make_user(), allow_project_creation=True)
        admin = self.make_user()
        self.add_org_member(org, admin, "ADMIN")
        self.assertOK(self.post(admin, "create-project", {"name": "P", "organization_id": str(org.id)}), 201)

    def test_non_member_of_org_is_refused_not_crashed(self):
        org = self.make_org(self.make_user())
        resp = self.post(self.make_user(), "create-project", {"name": "P", "organization_id": str(org.id)})
        self.assertOK(resp, 404)

    def test_unknown_org_is_404(self):
        resp = self.post(self.make_user(), "create-project",
                         {"name": "P", "organization_id": "00000000-0000-0000-0000-000000000000"})
        self.assertOK(resp, 404)

    def test_org_project_quota_is_enforced_and_deleted_projects_free_a_slot(self):
        owner = self.make_user()
        org = self.make_org(owner, max_projects=1)
        first = self.post(owner, "create-project", {"name": "one", "organization_id": str(org.id)})
        self.assertOK(first, 201)
        self.assertOK(self.post(owner, "create-project", {"name": "two", "organization_id": str(org.id)}), 400)

        self.assertOK(self.delete(owner, "delete-project", {"project_id": first.data["data"]["id"]}))
        self.assertOK(self.post(owner, "create-project", {"name": "three", "organization_id": str(org.id)}), 201)

    def test_quota_blocks_even_when_already_over_the_limit(self):
        owner = self.make_user()
        org = self.make_org(owner, max_projects=1)
        self.make_project(owner, org=org)
        self.make_project(owner, org=org)  # over the limit already (e.g. limit lowered later)
        self.assertOK(self.post(owner, "create-project", {"name": "x", "organization_id": str(org.id)}), 400)

    # ---- under a team ----
    def test_team_owner_creates_project_owned_by_that_team(self):
        owner = self.make_user()
        team = self.make_team(owner)
        resp = self.post(owner, "create-project", {"name": "P", "team_id": str(team.id), "team_role": "LEAD"})
        self.assertOK(resp, 201)
        link = ProjectTeam.objects.get(project_id=resp.data["data"]["id"])
        self.assertEqual((link.team, link.role, link.is_owning), (team, "LEAD", True))
        self.assertEqual(resp.data["data"]["team"], team.id)
        self.assertEqual(resp.data["data"]["team_role"], "LEAD")

    def test_team_link_role_defaults_to_contributor(self):
        owner = self.make_user()
        team = self.make_team(owner)
        resp = self.post(owner, "create-project", {"name": "P", "team_id": str(team.id)})
        self.assertOK(resp, 201)
        self.assertEqual(ProjectTeam.objects.get(project_id=resp.data["data"]["id"]).role, "CONTRIBUTOR")

    def test_team_role_without_team_is_rejected(self):
        self.assertOK(self.post(self.make_user(), "create-project", {"name": "P", "team_role": "LEAD"}), 400)

    def test_team_link_role_cannot_be_owner_or_guest(self):
        owner = self.make_user()
        team = self.make_team(owner)
        for bad in ("OWNER", "GUEST", "NOPE"):
            resp = self.post(owner, "create-project", {"name": "P", "team_id": str(team.id), "team_role": bad})
            self.assertOK(resp, 400)

    def test_team_non_member_is_refused(self):
        team = self.make_team(self.make_user())
        self.assertOK(self.post(self.make_user(), "create-project", {"name": "P", "team_id": str(team.id)}), 404)

    def test_team_member_needs_the_team_to_allow_project_creation(self):
        team = self.make_team(self.make_user())
        manager = self.make_user()
        self.add_team_member(team, manager, "MANAGER")
        self.assertOK(self.post(manager, "create-project", {"name": "P", "team_id": str(team.id)}), 400)
        self.set_settings(team, allow_project_creation=True)
        self.assertOK(self.post(manager, "create-project", {"name": "P", "team_id": str(team.id)}), 201)

    def test_team_member_below_min_role_cannot_create_even_if_allowed(self):
        team = self.make_team(self.make_user(), allow_project_creation=True)
        member = self.make_user()
        self.add_team_member(team, member, "MEMBER")
        self.assertOK(self.post(member, "create-project", {"name": "P", "team_id": str(team.id)}), 400)

    def test_team_project_quota(self):
        owner = self.make_user()
        team = self.make_team(owner, max_projects=1)
        self.assertOK(self.post(owner, "create-project", {"name": "1", "team_id": str(team.id)}), 201)
        self.assertOK(self.post(owner, "create-project", {"name": "2", "team_id": str(team.id)}), 400)

    def test_team_from_a_different_org_is_rejected(self):
        owner = self.make_user()
        org1, org2 = self.make_org(owner), self.make_org(owner)
        team_in_org2 = self.make_team(owner, org=org2)
        resp = self.post(owner, "create-project",
                         {"name": "P", "organization_id": str(org1.id), "team_id": str(team_in_org2.id)})
        self.assertOK(resp, 400)

    def test_team_in_same_org_is_linked(self):
        owner = self.make_user()
        org = self.make_org(owner)
        team = self.make_team(owner, org=org)
        resp = self.post(owner, "create-project",
                         {"name": "P", "organization_id": str(org.id), "team_id": str(team.id)})
        self.assertOK(resp, 201)
        project = Project.objects.get(id=resp.data["data"]["id"])
        self.assertEqual((project.organization, project.team), (org, team))

    def test_soft_deleted_team_cannot_be_used(self):
        owner = self.make_user()
        team = self.make_team(owner)
        team.is_deleted = True
        team.save()
        self.assertOK(self.post(owner, "create-project", {"name": "P", "team_id": str(team.id)}), 400)

    def test_a_failure_while_linking_the_team_leaves_no_half_created_project(self):
        owner = self.make_user()
        team = self.make_team(owner)
        client = self.client_for(owner)
        with mock.patch("app.projects.api.v1.serializers.assign_team", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                client.post(purl("create-project"), {"name": "P", "team_id": str(team.id)}, format="json")
        self.assertEqual(Project.objects.count(), 0)


class ProjectListTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def test_lists_only_projects_the_user_belongs_to(self):
        mine = self.make_project(self.user)
        self.make_project(self.make_user())
        resp = self.get(self.user, "get-user-projects")
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(mine.id)})

    def test_includes_projects_reached_through_a_team_without_a_membership_row(self):
        team = self.make_team(self.make_user())
        self.add_team_member(team, self.user)
        derived = self.make_project(self.make_user(), team=team)
        self.assertFalse(ProjectMembership.objects.filter(project=derived, user=self.user).exists())
        self.assertIn(str(derived.id), ids(self.get(self.user, "get-user-projects")))

    def test_a_project_reachable_two_ways_is_listed_once(self):
        team = self.make_team(self.make_user())
        self.add_team_member(team, self.user)
        project = self.make_project(self.make_user(), team=team)
        self.add_project_member(project, self.user, "LEAD")
        resp = self.get(self.user, "get-user-projects")
        self.assertEqual([str(i["id"]) for i in results(resp)].count(str(project.id)), 1)

    def test_deleted_team_no_longer_lists_its_projects(self):
        team = self.make_team(self.make_user())
        self.add_team_member(team, self.user)
        derived = self.make_project(self.make_user(), team=team)
        team.is_deleted = True
        team.save()
        self.assertNotIn(str(derived.id), ids(self.get(self.user, "get-user-projects")))

    def test_excludes_deleted_projects(self):
        gone = self.make_project(self.user)
        gone.is_deleted = True
        gone.save()
        self.assertEqual(ids(self.get(self.user, "get-user-projects")), set())

    def test_filter_by_status_and_search(self):
        active = self.make_project(self.user, name="Rocket")
        active.status = "ACTIVE"
        active.save()
        self.make_project(self.user, name="Garden")
        self.assertEqual(ids(self.get(self.user, "get-user-projects", status="ACTIVE")), {str(active.id)})
        self.assertEqual(ids(self.get(self.user, "get-user-projects", search="rock")), {str(active.id)})

    def test_pagination_shape(self):
        for i in range(3):
            self.make_project(self.user, name=f"P{i}")
        resp = self.get(self.user, "get-user-projects", page_size=2)
        self.assertEqual(resp.data["count"], 3)
        self.assertIsNotNone(resp.data["next"])
        self.assertEqual(len(results(resp)), 2)
        self.assertEqual(resp.data["results"]["message"], "Success")

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(purl("get-user-projects")), 401)


class ProjectRetrieveTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.creator = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.creator, "MANAGER")
        self.project = self.make_project(self.creator, org=self.org)

    def test_explicit_member_can_read(self):
        resp = self.get(self.creator, "get-project-details", project_id=self.project.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["name"], self.project.name)
        self.assertEqual(resp.data["data"]["organization_name"], self.org.name)

    def test_any_org_member_can_read_an_org_project(self):
        viewer = self.make_user()
        self.add_org_member(self.org, viewer, "VIEWER")
        self.assertOK(self.get(viewer, "get-project-details", project_id=self.project.id))

    def test_team_derived_participant_can_read(self):
        """Used to 500: the membership lookup raised a bare Exception for team-derived users."""
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        project = self.make_project(self.creator, team=team)
        self.assertOK(self.get(member, "get-project-details", project_id=project.id))

    def test_outsider_gets_403_not_500(self):
        self.assertDenied(self.get(self.make_user(), "get-project-details", project_id=self.project.id))

    def test_owner_of_a_different_org_cannot_read(self):
        stranger = self.make_user()
        self.make_org(stranger)
        self.assertDenied(self.get(stranger, "get-project-details", project_id=self.project.id))

    def test_unknown_project_is_404(self):
        resp = self.get(self.creator, "get-project-details", project_id="00000000-0000-0000-0000-000000000000")
        self.assertOK(resp, 404)

    def test_malformed_project_id_is_404_not_500(self):
        self.assertOK(self.get(self.creator, "get-project-details", project_id="not-a-uuid"), 404)

    def test_missing_project_id_is_400(self):
        self.assertOK(self.get(self.creator, "get-project-details"), 400)

    def test_deleted_project_is_404(self):
        self.project.is_deleted = True
        self.project.save()
        self.assertOK(self.get(self.creator, "get-project-details", project_id=self.project.id), 404)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(purl("get-project-details", project_id=self.project.id)), 401)


class ProjectUpdateTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.owner = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.owner, "MANAGER")
        self.project = self.make_project(self.owner, org=self.org)

    def body(self, **extra):
        return {"project_id": str(self.project.id), **extra}

    def test_owner_can_update_fields(self):
        resp = self.put(self.owner, "update-project", self.body(name="Renamed", description="d2", status="ACTIVE"))
        self.assertOK(resp)
        self.project.refresh_from_db()
        self.assertEqual((self.project.name, self.project.description, self.project.status), ("Renamed", "d2", "ACTIVE"))

    def test_invalid_status_is_rejected(self):
        self.assertOK(self.put(self.owner, "update-project", self.body(status="WHATEVER")), 400)

    def test_manager_cannot_update(self):
        manager = self.make_user()
        self.add_project_member(self.project, manager, "MANAGER")
        self.assertDenied(self.put(manager, "update-project", self.body(name="x")))

    def test_viewer_and_outsider_cannot_update(self):
        viewer = self.make_user()
        self.add_project_member(self.project, viewer, "VIEWER")
        self.assertDenied(self.put(viewer, "update-project", self.body(name="x")))
        self.assertDenied(self.put(self.make_user(), "update-project", self.body(name="x")))

    def test_org_owner_backstop_can_update(self):
        self.assertOK(self.put(self.org_owner, "update-project", self.body(name="By backstop")))

    def test_unknown_project_is_404_and_missing_is_400(self):
        self.assertOK(self.put(self.owner, "update-project", {"project_id": "00000000-0000-0000-0000-000000000000"}), 404)
        self.assertOK(self.put(self.owner, "update-project", {"name": "x"}), 400)

    def test_owner_who_is_not_on_a_team_cannot_attach_it(self):
        """Attaching (and making 'owning') someone else's team needs the same authority as assign-team."""
        foreign_team = self.make_team(self.make_user(), org=self.org)
        resp = self.put(self.owner, "update-project", self.body(team_id=str(foreign_team.id)))
        self.assertOK(resp, 400)
        self.assertEqual(ProjectTeam.objects.filter(project=self.project).count(), 0)

    def test_owner_can_attach_a_team_they_manage(self):
        team = self.make_team(self.owner, org=self.org)
        resp = self.put(self.owner, "update-project", self.body(team_id=str(team.id), team_role="LEAD"))
        self.assertOK(resp)
        link = ProjectTeam.objects.get(project=self.project)
        self.assertEqual((link.team, link.role, link.is_owning), (team, "LEAD", True))

    def test_team_from_another_org_is_rejected(self):
        other_org = self.make_org(self.owner)
        team = self.make_team(self.owner, org=other_org)
        self.assertOK(self.put(self.owner, "update-project", self.body(team_id=str(team.id))), 400)

    def test_team_id_null_unassigns_the_owning_team(self):
        team = self.make_team(self.owner, org=self.org)
        project = self.make_project(self.owner, org=self.org, team=team)
        resp = self.put(self.owner, "update-project", {"project_id": str(project.id), "team_id": None})
        self.assertOK(resp)
        self.assertEqual(ProjectTeam.objects.filter(project=project).count(), 0)

    def test_resubmitting_the_current_team_is_allowed(self):
        team = self.make_team(self.owner, org=self.org)
        project = self.make_project(self.owner, org=self.org, team=team)
        resp = self.put(self.owner, "update-project", {"project_id": str(project.id), "team_id": str(team.id)})
        self.assertOK(resp)

    def test_team_role_alone_updates_the_owning_link(self):
        team = self.make_team(self.owner, org=self.org)
        project = self.make_project(self.owner, org=self.org, team=team, team_role="VIEWER")
        self.assertOK(self.put(self.owner, "update-project", {"project_id": str(project.id), "team_role": "LEAD"}))
        self.assertEqual(ProjectTeam.objects.get(project=project).role, "LEAD")

    def test_team_role_without_a_team_is_rejected(self):
        self.assertOK(self.put(self.owner, "update-project", self.body(team_role="LEAD")), 400)


class ProjectDeleteTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.org_owner, self.creator = self.make_user(), self.make_user()
        self.org = self.make_org(self.org_owner)
        self.add_org_member(self.org, self.creator, "MANAGER")
        self.project = self.make_project(self.creator, org=self.org)

    def remove(self, user, project=None):
        return self.delete(user, "delete-project", {"project_id": str((project or self.project).id)})

    def test_creator_can_delete_and_it_is_a_soft_delete(self):
        self.assertOK(self.remove(self.creator))
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_deleted)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.assertOK(self.get(self.creator, "get-project-details", project_id=self.project.id), 404)
        self.assertEqual(ids(self.get(self.creator, "get-user-projects")), set())

    def test_deleting_twice_is_404(self):
        self.assertOK(self.remove(self.creator))
        self.assertOK(self.remove(self.creator), 404)

    def test_org_owner_backstop_can_delete_a_project_they_are_not_in(self):
        """REGRESSION: the permission class admitted the backstop but delete_project() rejected them."""
        self.assertFalse(ProjectMembership.objects.filter(project=self.project, user=self.org_owner).exists())
        self.assertOK(self.remove(self.org_owner))
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_deleted)

    def test_owning_team_owner_backstop_can_delete(self):
        t_owner = self.make_user()
        team = self.make_team(t_owner)
        project = self.make_project(self.creator, team=team)
        self.assertOK(self.remove(t_owner, project))

    def test_owner_of_a_non_owning_assigned_team_cannot_delete(self):
        owning_owner, other_owner = self.make_user(), self.make_user()
        owning, other = self.make_team(owning_owner), self.make_team(other_owner)
        project = self.make_project(self.creator, team=owning)
        assign_team(project=project, team=other, role="VIEWER", is_owning=False, assigned_by=self.creator)
        self.assertDenied(self.remove(other_owner, project))
        project.refresh_from_db()
        self.assertFalse(project.is_deleted)

    def test_org_admin_manager_and_stranger_cannot_delete(self):
        admin, manager, stranger = self.make_user(), self.make_user(), self.make_user()
        self.add_org_member(self.org, admin, "ADMIN")
        self.add_project_member(self.project, manager, "MANAGER")
        for user in (admin, manager, stranger):
            self.assertDenied(self.remove(user))
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_deleted)

    def test_requires_authentication(self):
        resp = self.anon().delete(purl("delete-project"), {"project_id": str(self.project.id)}, format="json")
        self.assertDenied(resp, 401)


class ProjectTransferOwnerTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.creator = self.make_user()
        self.project = self.make_project(self.creator)
        self.heir = self.make_user()
        self.add_project_member(self.project, self.heir, "MANAGER")

    def transfer(self, user, email, project=None):
        return self.put(user, "transfer-owner", {"email": email}, project_id=(project or self.project).id)

    def test_creator_hands_over_ownership(self):
        self.assertOK(self.transfer(self.creator, self.heir.email))
        self.project.refresh_from_db()
        self.assertEqual(self.project.created_by, self.heir)
        roles = {m.user_id: m.role for m in self.project.memberships.all()}
        self.assertEqual(roles[self.heir.id], "OWNER")
        self.assertEqual(roles[self.creator.id], "MANAGER")

    def test_previous_owner_loses_owner_powers(self):
        self.assertOK(self.transfer(self.creator, self.heir.email))
        self.assertDenied(self.delete(self.creator, "delete-project", {"project_id": str(self.project.id)}))
        self.assertOK(self.delete(self.heir, "delete-project", {"project_id": str(self.project.id)}))

    def test_target_must_already_be_a_member(self):
        self.assertOK(self.transfer(self.creator, self.make_user().email), 400)

    def test_cannot_transfer_to_self(self):
        self.assertOK(self.transfer(self.creator, self.creator.email), 400)

    def test_unknown_email_is_404(self):
        self.assertOK(self.transfer(self.creator, "nobody@example.com"), 404)

    def test_manager_and_stranger_cannot_transfer(self):
        """REGRESSION: the action name in get_permissions() never matched, so this ran unprotected."""
        self.assertDenied(self.transfer(self.heir, self.heir.email))
        self.assertDenied(self.transfer(self.make_user(), self.heir.email))

    def test_org_owner_backstop_can_transfer(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        self.add_org_member(org, self.creator, "MANAGER")
        self.add_org_member(org, self.heir, "MEMBER")
        project = self.make_project(self.creator, org=org)
        self.add_project_member(project, self.heir, "MANAGER")
        self.assertOK(self.transfer(org_owner, self.heir.email, project))
        project.refresh_from_db()
        self.assertEqual(project.created_by, self.heir)

    def test_in_an_org_the_new_owner_must_be_an_org_member(self):
        org = self.make_org(self.make_user())
        self.add_org_member(org, self.creator, "MANAGER")
        project = self.make_project(self.creator, org=org)
        self.add_project_member(project, self.heir, "MANAGER")  # project member, but not in the org
        self.assertOK(self.transfer(self.creator, self.heir.email, project), 400)


class OrgAndTeamProjectListingTests(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)

    def test_org_members_see_the_orgs_live_projects(self):
        live = self.make_project(self.owner, org=self.org)
        dead = self.make_project(self.owner, org=self.org)
        dead.is_deleted = True
        dead.save()
        self.make_project(self.owner)  # different (standalone) project
        member = self.make_user()
        self.add_org_member(self.org, member, "VIEWER")
        resp = self.get(member, "get_org-projects", org_id=self.org.id)
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(live.id)})

    def test_org_listing_is_for_org_members_only(self):
        self.assertDenied(self.get(self.make_user(), "get_org-projects", org_id=self.org.id))
        self.assertOK(self.get(self.owner, "get_org-projects", org_id="00000000-0000-0000-0000-000000000000"), 404)

    def test_team_members_see_every_project_the_team_is_assigned_to(self):
        t_owner = self.make_user()
        team = self.make_team(t_owner)
        owning = self.make_project(self.owner, team=team)
        shared = self.make_project(self.owner)
        assign_team(project=shared, team=team, role="VIEWER", is_owning=False, assigned_by=self.owner)
        self.make_project(self.owner)  # unrelated
        resp = self.get(t_owner, "get-team-projects", team_id=team.id)
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(owning.id), str(shared.id)})

    def test_team_listing_is_for_team_members_only(self):
        team = self.make_team(self.owner)
        self.assertDenied(self.get(self.make_user(), "get-team-projects", team_id=team.id))
