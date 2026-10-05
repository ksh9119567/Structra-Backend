"""
Profile endpoints: get-user, update_user, delete_user (soft delete + its guards).
"""
from .helpers import AccountAPITestCase, aurl


class GetUserTests(AccountAPITestCase):
    def test_returns_the_profile(self):
        user = self.make_user(email="me@example.com", first_name="Me", phone_no="+15551234567")
        resp = self.client_for(user).get(aurl("get-user"))
        self.assertOK(resp)
        data = resp.data["data"]
        self.assertEqual((data["email"], data["first_name"], data["phone_number"]), ("me@example.com", "Me", "+15551234567"))
        self.assertTrue(data["is_email_verified"])
        self.assertNotIn("password", data)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().get(aurl("get-user")), 401)


class UpdateUserTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="upd@example.com")

    def update(self, **data):
        return self.client_for(self.user).put(aurl("update_user"), data, format="json")

    def test_updates_profile_fields(self):
        resp = self.update(first_name="Ada", last_name="Lovelace", username="ada")
        self.assertOK(resp)
        user = self.fresh(self.user)
        self.assertEqual((user.first_name, user.last_name, user.username), ("Ada", "Lovelace", "ada"))
        self.assertEqual(resp.data["data"]["first_name"], "Ada")

    def test_partial_update_leaves_other_fields_alone(self):
        self.update(first_name="Ada")
        self.assertEqual(self.fresh(self.user).last_name, self.user.last_name)

    def test_email_and_privileged_flags_cannot_be_changed(self):
        self.update(email="evil@example.com", is_staff=True, is_superuser=True, is_email_verified=False, is_active=False)
        user = self.fresh(self.user)
        self.assertEqual(user.email, "upd@example.com")
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertTrue(user.is_email_verified and user.is_active)

    def test_changing_the_phone_number_resets_its_verification(self):
        self.user.phone_no, self.user.is_phone_verified = "+15550000001", True
        self.user.save()
        self.assertOK(self.update(phone_number="+15559876543"))
        user = self.fresh(self.user)
        self.assertEqual(user.phone_no, "+15559876543")
        self.assertFalse(user.is_phone_verified)

    def test_phone_format_is_validated(self):
        self.assertOK(self.update(phone_number="abc"), 400)
        self.assertOK(self.update(phone_number="123"), 400)

    def test_phone_number_must_be_unique(self):
        self.make_user(phone_no="+15551112222")
        self.assertOK(self.update(phone_number="+15551112222"), 400)
        self.assertOK(self.update(phone_number="+15551112223"))

    def test_keeping_your_own_phone_number_is_fine(self):
        self.user.phone_no = "+15551112222"
        self.user.save()
        self.assertOK(self.update(phone_number="+15551112222"))

    def test_a_blank_phone_number_clears_it(self):
        self.user.phone_no = "+15551112222"
        self.user.save()
        self.assertOK(self.update(phone_number=""))
        self.assertEqual(self.fresh(self.user).phone_no, "")

    def test_requires_authentication(self):
        self.assertDenied(self.anon().put(aurl("update_user"), {"first_name": "x"}, format="json"), 401)


class DeleteUserTests(AccountAPITestCase):
    def delete(self, user):
        return self.client_for(user).delete(aurl("delete_user"))

    def test_a_plain_user_is_soft_deleted(self):
        user = self.make_user()
        self.assertOK(self.delete(user), 204)
        user = self.fresh(user)
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)

    def test_after_deletion_the_old_session_and_login_stop_working(self):
        user = self.make_user(email="gone@example.com")
        client = self.client_for(user)
        self.assertOK(client.delete(aurl("delete_user")), 204)
        self.assertOK(client.get(aurl("get-user")), 401)
        self.assertOK(self.login("gone@example.com"), 401)

    def test_a_member_of_an_org_team_and_project_can_delete(self):
        owner, user = self.make_user(), self.make_user()
        org = self.make_org(owner)
        self.add_org_member(org, user, "MEMBER")
        team = self.make_team(owner, org=org)
        self.add_team_member(team, user, "MEMBER")
        project = self.make_project(owner, org=org)
        self.add_project_member(project, user, "CONTRIBUTOR")
        self.assertOK(self.delete(user), 204)

    def test_an_org_owner_cannot_delete_their_account(self):
        """REGRESSION: the guards compared against lower-case role names and never matched."""
        owner = self.make_user()
        self.make_org(owner)
        resp = self.delete(owner)
        self.assertOK(resp, 400)
        self.assertIn("organization owner", str(resp.data))
        self.assertFalse(self.fresh(owner).is_deleted)

    def test_a_team_owner_cannot_delete_their_account(self):
        owner = self.make_user()
        self.make_team(owner)
        resp = self.delete(owner)
        self.assertOK(resp, 400)
        self.assertIn("team owner", str(resp.data))

    def test_a_project_owner_cannot_delete_their_account(self):
        owner = self.make_user()
        self.make_project(owner)
        resp = self.delete(owner)
        self.assertOK(resp, 400)
        self.assertIn("project owner", str(resp.data))

    def test_the_last_org_admin_cannot_delete_but_one_of_two_can(self):
        owner, admin, second = self.make_user(), self.make_user(), self.make_user()
        org = self.make_org(owner)
        self.add_org_member(org, admin, "ADMIN")
        resp = self.delete(admin)
        self.assertOK(resp, 400)
        self.assertIn("organization admin", str(resp.data))
        self.add_org_member(org, second, "ADMIN")
        self.assertOK(self.delete(admin), 204)

    def test_the_last_team_manager_cannot_delete_but_one_of_two_can(self):
        owner, manager, second = self.make_user(), self.make_user(), self.make_user()
        team = self.make_team(owner)
        self.add_team_member(team, manager, "MANAGER")
        self.assertOK(self.delete(manager), 400)
        self.add_team_member(team, second, "MANAGER")
        self.assertOK(self.delete(manager), 204)

    def test_the_last_project_manager_cannot_delete_but_one_of_two_can(self):
        owner, manager, second = self.make_user(), self.make_user(), self.make_user()
        project = self.make_project(owner)
        self.add_project_member(project, manager, "MANAGER")
        self.assertOK(self.delete(manager), 400)
        self.add_project_member(project, second, "MANAGER")
        self.assertOK(self.delete(manager), 204)

    def test_requires_authentication(self):
        self.assertDenied(self.anon().delete(aurl("delete_user")), 401)
