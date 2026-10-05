"""
Organization membership endpoints: members list, invites (+ role-escalation
guard), accept-invite, update-member, remove-member, self-remove.
"""
from django.core import mail

from app.organizations.models import OrganizationMembership
from .helpers import OrgAPITestCase, ourl, results


class OrgMemberTestBase(OrgAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)
        self.admin, self.manager, self.member, self.viewer = (self.make_user() for _ in range(4))
        self.add_org_member(self.org, self.admin, "ADMIN")
        self.add_org_member(self.org, self.manager, "MANAGER")
        self.add_org_member(self.org, self.member, "MEMBER")
        self.add_org_member(self.org, self.viewer, "VIEWER")
        self.outsider = self.make_user()

    def role_of(self, user, org=None):
        m = OrganizationMembership.objects.filter(organization=org or self.org, user=user).first()
        return m.role if m else None


class OrgMembersListTests(OrgMemberTestBase):
    def test_members_list_filter_and_search(self):
        resp = self.get(self.viewer, "get-org-members", org_id=self.org.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["count"], 5)
        resp = self.get(self.owner, "get-org-members", org_id=self.org.id, role="MANAGER")
        self.assertEqual([m["user_email"] for m in results(resp)], [self.manager.email])
        resp = self.get(self.owner, "get-org-members", org_id=self.org.id, search=self.member.email)
        self.assertEqual([m["user_email"] for m in results(resp)], [self.member.email])

    def test_outsider_is_refused(self):
        self.assertDenied(self.get(self.outsider, "get-org-members", org_id=self.org.id))


class OrgInviteTests(OrgMemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()

    def invite(self, actor, email=None, role=None):
        data = {"email": email or self.invitee.email}
        if role:
            data["role"] = role
        return self.post(actor, "sent-invite", data, org_id=self.org.id)

    def test_owner_invites_and_the_token_and_email_are_issued(self):
        resp = self.invite(self.owner)
        self.assertOK(resp)
        self.assertEqual(self.redis().exists(f"invite_token:organization:{resp.data['invite_token']}"), 1)
        self.assertEqual([m.to for m in mail.outbox], [[self.invitee.email]])

    def test_default_role_is_member(self):
        token = self.invite(self.owner).data["invite_token"]
        self.assertOK(self.post(self.invitee, "accept-org-invite", invite_token=token))
        self.assertEqual(self.role_of(self.invitee), "MEMBER")

    def test_admin_needs_the_org_to_allow_member_invites(self):
        resp = self.invite(self.admin)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to invite", str(resp.data))
        self.set_settings(self.org, allow_member_invites=True)
        self.assertOK(self.invite(self.admin))

    def test_manager_additionally_needs_a_lowered_threshold(self):
        self.set_settings(self.org, allow_member_invites=True)            # threshold defaults to ADMIN
        self.assertOK(self.invite(self.manager), 400)
        self.set_settings(self.org, invite_member_min_role="MANAGER")
        self.assertOK(self.invite(self.manager))

    def test_member_viewer_and_outsider_cannot_invite(self):
        self.set_settings(self.org, allow_member_invites=True, invite_member_min_role="MANAGER")
        for user in (self.member, self.viewer, self.outsider):
            self.assertDenied(self.invite(user))

    # ---- role-escalation guard ----
    def test_nobody_can_invite_straight_in_as_owner(self):
        self.set_settings(self.org, allow_member_invites=True)
        for actor in (self.owner, self.admin):
            resp = self.invite(actor, role="OWNER")
            self.assertOK(resp, 400)
            self.assertIn("Ownership", str(resp.data))

    def test_admin_cannot_invite_an_equal_role_but_can_invite_below(self):
        self.set_settings(self.org, allow_member_invites=True)
        self.assertOK(self.invite(self.admin, role="ADMIN"), 400)
        for role in ("MANAGER", "MEMBER", "VIEWER"):
            self.assertOK(self.invite(self.admin, email=self.make_user().email, role=role))

    def test_manager_cannot_invite_an_equal_or_higher_role(self):
        self.set_settings(self.org, allow_member_invites=True, invite_member_min_role="MANAGER")
        self.assertOK(self.invite(self.manager, role="MANAGER"), 400)
        self.assertOK(self.invite(self.manager, role="ADMIN"), 400)
        self.assertOK(self.invite(self.manager, role="MEMBER"))

    def test_owner_can_invite_an_admin(self):
        self.assertOK(self.invite(self.owner, role="ADMIN"))

    def test_bad_input(self):
        self.assertOK(self.invite(self.owner, role="BOSS"), 400)
        self.assertOK(self.invite(self.owner, email="ghost@example.com"), 404)
        self.assertOK(self.invite(self.owner, email=self.owner.email), 400)
        self.assertOK(self.invite(self.owner, email=self.viewer.email), 400)
        self.assertOK(self.invite(self.owner, email="not-an-email"), 400)

    def test_member_limit(self):
        self.set_settings(self.org, max_members=5)
        self.assertOK(self.invite(self.owner), 400)
        self.set_settings(self.org, max_members=6)
        self.assertOK(self.invite(self.owner))

    def test_requires_authentication(self):
        resp = self.anon().post(ourl("sent-invite", org_id=self.org.id), {"email": self.invitee.email}, format="json")
        self.assertDenied(resp, 401)


class OrgAcceptInviteTests(OrgMemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()
        resp = self.post(self.owner, "sent-invite", {"email": self.invitee.email, "role": "MANAGER"}, org_id=self.org.id)
        self.token = resp.data["invite_token"]

    def accept(self, user, token=None):
        return self.post(user, "accept-org-invite", invite_token=token or self.token)

    def test_invitee_joins_with_the_invited_role_and_the_token_is_single_use(self):
        resp = self.accept(self.invitee)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["role"], "MANAGER")
        self.assertEqual(self.role_of(self.invitee), "MANAGER")
        self.assertOK(self.accept(self.invitee), 400)

    def test_someone_elses_token_is_403_and_stays_usable(self):
        self.assertOK(self.accept(self.outsider), 403)
        self.assertIsNone(self.role_of(self.outsider))
        self.assertOK(self.accept(self.invitee))

    def test_unknown_missing_and_expired_tokens(self):
        self.assertOK(self.accept(self.invitee, token="deadbeef"), 400)
        self.assertOK(self.post(self.invitee, "accept-org-invite"), 400)
        self.redis().advance(24 * 3600 + 1)
        self.assertOK(self.accept(self.invitee), 400)

    def test_already_a_member_is_400_not_500(self):
        self.add_org_member(self.org, self.invitee, "VIEWER")
        self.assertOK(self.accept(self.invitee), 400)

    def test_org_deleted_before_accepting_is_404(self):
        self.org.is_deleted = True
        self.org.save()
        self.assertOK(self.accept(self.invitee), 404)

    def test_a_token_for_one_scope_cannot_be_redeemed_in_another(self):
        client = self.client_for(self.invitee)
        self.assertOK(client.post(f"/api/v1/teams/accept-team-invite/?invite_token={self.token}"), 400)
        self.assertOK(client.post(f"/api/v1/projects/accept-project-invite/?invite_token={self.token}"), 400)
        self.assertIsNone(self.role_of(self.invitee))


class OrgUpdateMemberTests(OrgMemberTestBase):
    def update(self, actor, target, role):
        return self.put(actor, "update-member", {"email": target.email, "role": role}, org_id=self.org.id)

    def test_owner_changes_a_role(self):
        self.assertOK(self.update(self.owner, self.member, "MANAGER"))
        self.assertEqual(self.role_of(self.member), "MANAGER")

    def test_admin_needs_the_org_to_allow_updates(self):
        resp = self.update(self.admin, self.member, "VIEWER")
        self.assertOK(resp, 400)
        self.assertIn("not allowed to update", str(resp.data))
        self.set_settings(self.org, allow_member_updates=True)
        self.assertOK(self.update(self.admin, self.member, "VIEWER"))

    def test_nobody_can_mint_an_owner_or_exceed_their_own_rank(self):
        self.set_settings(self.org, allow_member_updates=True)
        self.assertOK(self.update(self.owner, self.member, "OWNER"), 400)
        self.assertOK(self.update(self.admin, self.member, "ADMIN"), 400)

    def test_cannot_modify_an_equal_or_higher_member(self):
        self.set_settings(self.org, allow_member_updates=True)
        self.assertOK(self.update(self.admin, self.owner, "VIEWER"), 400)
        other_admin = self.make_user()
        self.add_org_member(self.org, other_admin, "ADMIN")
        self.assertOK(self.update(self.admin, other_admin, "VIEWER"), 400)

    def test_member_viewer_and_outsider_cannot_update(self):
        for user in (self.member, self.viewer, self.outsider):
            self.assertDenied(self.update(user, self.viewer, "MEMBER"))

    def test_a_manager_is_stopped_by_the_admin_only_policy(self):
        self.set_settings(self.org, allow_member_updates=True)
        resp = self.update(self.manager, self.member, "VIEWER")
        self.assertOK(resp, 400)
        self.assertIn("ADMIN", str(resp.data))

    def test_the_last_admin_cannot_be_downgraded(self):
        resp = self.update(self.owner, self.admin, "MEMBER")
        self.assertOK(resp, 400)
        self.assertIn("last remaining Admin", str(resp.data))

    def test_target_who_is_not_a_member_is_400_not_500(self):
        self.assertOK(self.update(self.owner, self.outsider, "MEMBER"), 400)

    def test_bad_input(self):
        self.assertOK(self.update(self.owner, self.member, "BOSS"), 400)
        self.assertOK(self.put(self.owner, "update-member", {"email": self.member.email}, org_id=self.org.id), 400)
        self.assertOK(self.put(self.owner, "update-member", {"email": "ghost@example.com", "role": "VIEWER"},
                               org_id=self.org.id), 404)


class OrgRemoveMemberTests(OrgMemberTestBase):
    def remove(self, actor, target):
        return self.delete(actor, "remove-member", {"email": target.email}, org_id=self.org.id)

    def test_owner_removes_members_of_any_lower_rank(self):
        for user in (self.viewer, self.member, self.manager):
            self.assertOK(self.remove(self.owner, user))
            self.assertIsNone(self.role_of(user))

    def test_admin_needs_the_org_to_allow_removal(self):
        resp = self.remove(self.admin, self.member)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to remove", str(resp.data))
        self.set_settings(self.org, allow_member_removal=True)
        self.assertOK(self.remove(self.admin, self.member))

    def test_cannot_remove_the_owner_or_an_equal_rank(self):
        self.set_settings(self.org, allow_member_removal=True)
        resp = self.remove(self.admin, self.owner)
        self.assertDenied(resp)
        other_admin = self.make_user()
        self.add_org_member(self.org, other_admin, "ADMIN")
        self.assertDenied(self.remove(self.admin, other_admin))

    def test_last_admin_cannot_be_removed(self):
        resp = self.remove(self.owner, self.admin)
        self.assertDenied(resp)
        self.assertIn("Last admin", str(resp.data))

    def test_lower_roles_and_outsiders_cannot_remove(self):
        for user in (self.member, self.viewer, self.outsider):
            self.assertDenied(self.remove(user, self.viewer))

    def test_a_non_member_is_a_clean_400_not_a_500(self):
        self.assertOK(self.remove(self.owner, self.outsider), 400)

    def test_unknown_email_is_404(self):
        self.assertOK(self.delete(self.owner, "remove-member", {"email": "ghost@example.com"}, org_id=self.org.id), 404)


class OrgSelfRemoveTests(OrgMemberTestBase):
    def leave(self, user):
        return self.delete(user, "self-remove-member", org_id=self.org.id)

    def test_off_by_default(self):
        self.assertDenied(self.leave(self.member))
        self.assertEqual(self.role_of(self.member), "MEMBER")

    def test_every_role_including_viewer_can_leave_when_allowed(self):
        """REGRESSION: the gate required MEMBER or above, so VIEWERs could never leave."""
        self.set_settings(self.org, allow_self_removal=True)
        for user in (self.viewer, self.member, self.manager):
            self.assertOK(self.leave(user))
            self.assertIsNone(self.role_of(user))

    def test_the_owner_cannot_leave(self):
        self.set_settings(self.org, allow_self_removal=True)
        self.assertDenied(self.leave(self.owner))

    def test_the_last_admin_cannot_leave(self):
        self.set_settings(self.org, allow_self_removal=True)
        self.assertDenied(self.leave(self.admin))

    def test_outsider_is_refused(self):
        self.set_settings(self.org, allow_self_removal=True)
        self.assertDenied(self.leave(self.outsider))
