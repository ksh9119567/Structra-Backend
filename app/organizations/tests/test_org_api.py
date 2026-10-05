"""
Organization CRUD endpoints: create, list, retrieve, update, delete, transfer-owner.
"""
from app.organizations.models import Organization, OrganizationMembership
from .helpers import OrgAPITestCase, ids, ourl, results


class OrgCreateTests(OrgAPITestCase):
    def test_creates_org_with_creator_as_owner(self):
        user = self.make_user()
        resp = self.post(user, "create-org", {"name": "Acme"})
        self.assertOK(resp, 201)
        org = Organization.objects.get(id=resp.data["data"]["id"])
        self.assertEqual((org.name, org.owner), ("Acme", user))
        self.assertEqual(OrganizationMembership.objects.get(organization=org, user=user).role, "OWNER")
        self.assertTrue(hasattr(org, "settings"))
        self.assertEqual(resp.data["data"]["owner_email"], user.email)
        self.assertEqual(resp.data["data"]["member_count"], 1)

    def test_name_is_required_and_must_be_unique_ignoring_case(self):
        user = self.make_user()
        self.assertOK(self.post(user, "create-org", {}), 400)
        self.assertOK(self.post(user, "create-org", {"name": "Acme"}), 201)
        self.assertOK(self.post(self.make_user(), "create-org", {"name": "ACME"}), 400)

    def test_a_deleted_orgs_name_can_be_reused(self):
        user = self.make_user()
        first = self.post(user, "create-org", {"name": "Acme"})
        self.assertOK(self.delete(user, "delete-org", org_id=first.data["data"]["id"]), 204)
        self.assertOK(self.post(user, "create-org", {"name": "Acme"}), 201)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().post(ourl("create-org"), {"name": "x"}, format="json"), 401)


class OrgListAndRetrieveTests(OrgAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner, name="Acme")

    def test_list_only_my_live_orgs(self):
        other = self.make_org(self.make_user())
        gone = self.make_org(self.owner)
        gone.is_deleted = True
        gone.save()
        resp = self.get(self.owner, "get-org")
        self.assertOK(resp)
        self.assertEqual(ids(resp), {str(self.org.id)})
        self.assertNotIn(str(other.id), ids(resp))

    def test_list_search(self):
        self.make_org(self.owner, name="Zebra Corp")
        self.assertEqual(len(results(self.get(self.owner, "get-org", search="zebra"))), 1)

    def test_member_of_any_role_can_retrieve(self):
        for role in ("ADMIN", "MANAGER", "MEMBER", "VIEWER"):
            user = self.make_user()
            self.add_org_member(self.org, user, role)
            resp = self.get(user, "get-org-details", org_id=self.org.id)
            self.assertOK(resp)
            self.assertEqual(resp.data["data"]["name"], "Acme")

    def test_counts_ignore_soft_deleted_teams_and_projects(self):
        live_team = self.make_team(self.owner, org=self.org)
        dead_team = self.make_team(self.owner, org=self.org)
        dead_team.is_deleted = True
        dead_team.save()
        live_project = self.make_project(self.owner, org=self.org)
        dead_project = self.make_project(self.owner, org=self.org)
        dead_project.is_deleted = True
        dead_project.save()
        data = self.get(self.owner, "get-org-details", org_id=self.org.id).data["data"]
        self.assertEqual((data["team_count"], data["project_count"]), (1, 1))
        self.assertIsNotNone((live_team, live_project))

    def test_outsider_and_missing_id_are_403_unknown_is_404(self):
        self.assertDenied(self.get(self.make_user(), "get-org-details", org_id=self.org.id))
        self.assertDenied(self.get(self.owner, "get-org-details"))
        self.assertOK(self.get(self.owner, "get-org-details", org_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-org-details", org_id="not-a-uuid"), 404)

    def test_deleted_org_is_404(self):
        self.org.is_deleted = True
        self.org.save()
        self.assertOK(self.get(self.owner, "get-org-details", org_id=self.org.id), 404)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(ourl("get-org")), 401)


class OrgUpdateTests(OrgAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner, name="Acme")

    def update(self, user, **data):
        return self.put(user, "update-org", data, org_id=self.org.id)

    def test_owner_renames(self):
        self.assertOK(self.update(self.owner, name="Acme Inc"))
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Acme Inc")

    def test_renaming_to_the_same_name_is_fine_but_a_taken_name_is_not(self):
        self.assertOK(self.update(self.owner, name="Acme"))
        self.make_org(self.make_user(), name="Taken")
        self.assertOK(self.update(self.owner, name="taken"), 400)

    def test_admin_manager_member_and_outsider_cannot_rename(self):
        for role in ("ADMIN", "MANAGER", "MEMBER", "VIEWER"):
            user = self.make_user()
            self.add_org_member(self.org, user, role)
            self.assertDenied(self.update(user, name="Hacked"))
        self.assertDenied(self.update(self.make_user(), name="Hacked"))
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Acme")


class OrgDeleteTests(OrgAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)

    def test_owner_deletes_softly(self):
        self.assertOK(self.delete(self.owner, "delete-org", org_id=self.org.id), 204)
        self.org.refresh_from_db()
        self.assertTrue(self.org.is_deleted)
        self.assertEqual(ids(self.get(self.owner, "get-org")), set())

    def test_only_the_owner_can_delete(self):
        admin = self.make_user()
        self.add_org_member(self.org, admin, "ADMIN")
        self.assertDenied(self.delete(admin, "delete-org", org_id=self.org.id))
        self.assertDenied(self.delete(self.make_user(), "delete-org", org_id=self.org.id))
        self.org.refresh_from_db()
        self.assertFalse(self.org.is_deleted)

    def test_deleting_twice_is_404(self):
        self.assertOK(self.delete(self.owner, "delete-org", org_id=self.org.id), 204)
        self.assertOK(self.delete(self.owner, "delete-org", org_id=self.org.id), 404)


class OrgTransferOwnerTests(OrgAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner, self.admin = self.make_user(), self.make_user()
        self.org = self.make_org(self.owner)
        self.add_org_member(self.org, self.admin, "ADMIN")

    def transfer(self, user, email):
        return self.put(user, "update-owner", {"email": email}, org_id=self.org.id)

    def test_owner_hands_over(self):
        self.assertOK(self.transfer(self.owner, self.admin.email))
        self.org.refresh_from_db()
        self.assertEqual(self.org.owner, self.admin)
        roles = {m.user_id: m.role for m in self.org.memberships.all()}
        self.assertEqual(roles[self.admin.id], "OWNER")
        self.assertEqual(roles[self.owner.id], "ADMIN")

    def test_previous_owner_loses_owner_powers(self):
        self.assertOK(self.transfer(self.owner, self.admin.email))
        self.assertDenied(self.put(self.owner, "update-org", {"name": "x"}, org_id=self.org.id))
        self.assertOK(self.put(self.admin, "update-org", {"name": "x"}, org_id=self.org.id))

    def test_only_the_owner_can_transfer(self):
        self.assertDenied(self.transfer(self.admin, self.admin.email))
        self.assertDenied(self.transfer(self.make_user(), self.admin.email))

    def test_validation(self):
        self.assertOK(self.transfer(self.owner, self.owner.email), 400)
        self.assertOK(self.transfer(self.owner, self.make_user().email), 400)     # not a member
        self.assertOK(self.transfer(self.owner, "ghost@example.com"), 404)
