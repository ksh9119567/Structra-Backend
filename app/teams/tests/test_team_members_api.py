"""
Team membership endpoints: members list, invites (+ role-escalation guard),
accept-invite, update-member, remove-member, self-remove.
"""
from django.core import mail

from app.teams.models import TeamMembership
from .helpers import TeamAPITestCase, results, turl


class TeamMemberTestBase(TeamAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.team = self.make_team(self.owner)
        self.manager, self.lead, self.member, self.viewer = (self.make_user() for _ in range(4))
        self.add_team_member(self.team, self.manager, "MANAGER")
        self.add_team_member(self.team, self.lead, "LEAD")
        self.add_team_member(self.team, self.member, "MEMBER")
        self.add_team_member(self.team, self.viewer, "VIEWER")
        self.outsider = self.make_user()

    def role_of(self, user, team=None):
        m = TeamMembership.objects.filter(team=team or self.team, user=user).first()
        return m.role if m else None


class TeamMembersListTests(TeamMemberTestBase):
    def test_members_can_list_filter_and_search(self):
        resp = self.get(self.viewer, "get-team-members", team_id=self.team.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["count"], 5)
        resp = self.get(self.owner, "get-team-members", team_id=self.team.id, role="LEAD")
        self.assertEqual([m["user_email"] for m in results(resp)], [self.lead.email])
        resp = self.get(self.owner, "get-team-members", team_id=self.team.id, search=self.viewer.email)
        self.assertEqual([m["user_email"] for m in results(resp)], [self.viewer.email])

    def test_outsider_is_refused(self):
        self.assertDenied(self.get(self.outsider, "get-team-members", team_id=self.team.id))


class TeamInviteTests(TeamMemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()

    def invite(self, actor, email=None, role=None, team=None):
        data = {"team_id": str((team or self.team).id), "email": email or self.invitee.email}
        if role:
            data["role"] = role
        return self.post(actor, "sent-invite", data)

    def test_owner_invites_and_the_token_and_email_are_issued(self):
        resp = self.invite(self.owner)
        self.assertOK(resp)
        self.assertEqual(self.redis().exists(f"invite_token:team:{resp.data['invite_token']}"), 1)
        self.assertEqual([m.to for m in mail.outbox], [[self.invitee.email]])

    def test_default_role_is_member(self):
        token = self.invite(self.owner).data["invite_token"]
        self.assertOK(self.post(self.invitee, "accept-team-invite", invite_token=token))
        self.assertEqual(self.role_of(self.invitee), "MEMBER")

    def test_manager_needs_the_team_to_allow_member_invites(self):
        resp = self.invite(self.manager)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to invite", str(resp.data))
        self.set_settings(self.team, allow_member_invites=True)
        self.assertOK(self.invite(self.manager))

    def test_lead_member_viewer_and_outsider_cannot_invite(self):
        self.set_settings(self.team, allow_member_invites=True)
        for user in (self.lead, self.member, self.viewer, self.outsider):
            self.assertDenied(self.invite(user))

    def test_org_owner_backstop_invites_without_being_a_team_member(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        team = self.make_team(self.owner, org=org)
        self.assertOK(self.invite(org_owner, team=team))

    def test_an_org_member_who_lost_their_org_seat_is_not_a_crash(self):
        """The old code did get_org_membership() and 404'd for a team manager no longer in the org."""
        org = self.make_org(self.make_user())
        team = self.make_team(self.owner, org=org)
        ex_member = self.make_user()
        self.add_team_member(team, ex_member, "MANAGER")      # on the team, but not in the org
        self.set_settings(team, allow_member_invites=True)
        self.assertOK(self.invite(ex_member, team=team))

    # ---- role-escalation guard ----
    def test_nobody_can_invite_straight_in_as_owner(self):
        self.set_settings(self.team, allow_member_invites=True)
        for actor in (self.owner, self.manager):
            resp = self.invite(actor, role="OWNER")
            self.assertOK(resp, 400)
            self.assertIn("Ownership", str(resp.data))

    def test_manager_cannot_invite_an_equal_role_but_can_invite_below(self):
        self.set_settings(self.team, allow_member_invites=True)
        self.assertOK(self.invite(self.manager, role="MANAGER"), 400)
        for role in ("LEAD", "MEMBER", "VIEWER"):
            self.assertOK(self.invite(self.manager, email=self.make_user().email, role=role))

    def test_owner_can_invite_a_manager(self):
        self.assertOK(self.invite(self.owner, role="MANAGER"))

    # ---- validation ----
    def test_bad_input(self):
        self.assertOK(self.invite(self.owner, role="BOSS"), 400)
        self.assertOK(self.invite(self.owner, email="ghost@example.com"), 404)
        self.assertOK(self.invite(self.owner, email=self.owner.email), 400)
        self.assertOK(self.invite(self.owner, email=self.viewer.email), 400)
        self.assertOK(self.invite(self.owner, email="not-an-email"), 400)

    def test_member_limit(self):
        self.set_settings(self.team, max_members=5)
        self.assertOK(self.invite(self.owner), 400)
        self.set_settings(self.team, max_members=6)
        self.assertOK(self.invite(self.owner))

    def test_requires_authentication(self):
        resp = self.anon().post(turl("sent-invite"), {"team_id": str(self.team.id), "email": self.invitee.email}, format="json")
        self.assertDenied(resp, 401)


class TeamAcceptInviteTests(TeamMemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()
        resp = self.post(self.owner, "sent-invite", {"team_id": str(self.team.id), "email": self.invitee.email, "role": "LEAD"})
        self.token = resp.data["invite_token"]

    def accept(self, user, token=None):
        return self.post(user, "accept-team-invite", invite_token=token or self.token)

    def test_invitee_joins_with_the_invited_role_and_the_token_is_single_use(self):
        resp = self.accept(self.invitee)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["role"], "LEAD")
        self.assertEqual(self.role_of(self.invitee), "LEAD")
        self.assertOK(self.accept(self.invitee), 400)

    def test_someone_elses_token_is_403_and_stays_usable(self):
        self.assertOK(self.accept(self.outsider), 403)
        self.assertIsNone(self.role_of(self.outsider))
        self.assertOK(self.accept(self.invitee))

    def test_unknown_missing_and_expired_tokens(self):
        self.assertOK(self.accept(self.invitee, token="deadbeef"), 400)
        self.assertOK(self.post(self.invitee, "accept-team-invite"), 400)
        self.redis().advance(24 * 3600 + 1)
        self.assertOK(self.accept(self.invitee), 400)

    def test_already_a_member_is_400_not_500(self):
        self.add_team_member(self.team, self.invitee, "VIEWER")
        self.assertOK(self.accept(self.invitee), 400)

    def test_team_deleted_before_accepting_is_404(self):
        self.team.is_deleted = True
        self.team.save()
        self.assertOK(self.accept(self.invitee), 404)


class TeamUpdateMemberTests(TeamMemberTestBase):
    def update(self, actor, target, role, team=None):
        return self.put(actor, "update-member", {"email": target.email, "role": role}, team_id=(team or self.team).id)

    def test_owner_changes_a_role(self):
        self.assertOK(self.update(self.owner, self.member, "LEAD"))
        self.assertEqual(self.role_of(self.member), "LEAD")

    def test_manager_needs_the_team_to_allow_updates(self):
        resp = self.update(self.manager, self.member, "LEAD")
        self.assertOK(resp, 400)
        self.assertIn("not allowed to update", str(resp.data))
        self.set_settings(self.team, allow_member_updates=True)
        self.assertOK(self.update(self.manager, self.member, "LEAD"))

    def test_manager_cannot_grant_an_equal_or_higher_role(self):
        self.set_settings(self.team, allow_member_updates=True)
        self.assertOK(self.update(self.manager, self.member, "MANAGER"), 400)
        self.assertOK(self.update(self.manager, self.member, "OWNER"), 400)

    def test_manager_cannot_touch_an_equal_or_higher_member(self):
        self.set_settings(self.team, allow_member_updates=True)
        other = self.make_user()
        self.add_team_member(self.team, other, "MANAGER")
        self.assertOK(self.update(self.manager, other, "VIEWER"), 400)
        self.assertOK(self.update(self.manager, self.owner, "VIEWER"), 400)

    def test_lower_roles_and_outsiders_cannot_update(self):
        for user in (self.lead, self.member, self.viewer, self.outsider):
            self.assertDenied(self.update(user, self.viewer, "MEMBER"))

    def test_the_last_manager_cannot_be_downgraded(self):
        resp = self.update(self.owner, self.manager, "LEAD")
        self.assertOK(resp, 400)
        self.assertIn("last remaining manager", str(resp.data))

    def test_org_owner_backstop_can_update_without_being_a_team_member(self):
        """REGRESSION: the serializer indexed the hierarchy with None and returned HTTP 500."""
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        team = self.make_team(self.owner, org=org)
        member = self.add_team_member(team, self.make_user(), "MEMBER").user
        self.assertOK(self.update(org_owner, member, "LEAD", team))
        self.assertEqual(self.role_of(member, team), "LEAD")

    def test_target_who_is_not_a_member_is_400_not_500(self):
        self.assertOK(self.update(self.owner, self.outsider, "MEMBER"), 400)

    def test_bad_input(self):
        self.assertOK(self.update(self.owner, self.member, "BOSS"), 400)
        self.assertOK(self.put(self.owner, "update-member", {"email": self.member.email}, team_id=self.team.id), 400)
        self.assertOK(self.put(self.owner, "update-member", {"email": "ghost@example.com", "role": "LEAD"},
                               team_id=self.team.id), 404)


class TeamRemoveMemberTests(TeamMemberTestBase):
    def remove(self, actor, target, team=None):
        return self.delete(actor, "remove-member", {"team_id": str((team or self.team).id), "email": target.email})

    def test_owner_removes_members_of_any_lower_rank(self):
        """REGRESSION: remove_team_member() contained a leftover `ipdb.set_trace()` that froze the request."""
        for user in (self.member, self.viewer, self.lead):
            self.assertOK(self.remove(self.owner, user))
            self.assertIsNone(self.role_of(user))

    def test_manager_needs_the_team_to_allow_removal(self):
        resp = self.remove(self.manager, self.member)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to remove", str(resp.data))
        self.set_settings(self.team, allow_member_removal=True)
        self.assertOK(self.remove(self.manager, self.member))

    def test_manager_cannot_remove_an_equal_or_higher_member(self):
        self.set_settings(self.team, allow_member_removal=True)
        other = self.make_user()
        self.add_team_member(self.team, other, "MANAGER")
        self.assertDenied(self.remove(self.manager, other))

    def test_the_creator_can_never_be_removed(self):
        self.set_settings(self.team, allow_member_removal=True)
        resp = self.remove(self.manager, self.owner)
        self.assertDenied(resp)
        self.assertIn("creator", str(resp.data))

    def test_lower_roles_and_outsiders_cannot_remove(self):
        for user in (self.lead, self.member, self.outsider):
            self.assertDenied(self.remove(user, self.viewer))

    def test_the_last_manager_cannot_be_removed(self):
        resp = self.remove(self.owner, self.manager)
        self.assertDenied(resp)
        self.assertIn("Last manager", str(resp.data))

    def test_a_non_member_is_a_clean_400_not_a_500(self):
        self.assertOK(self.remove(self.owner, self.outsider), 400)

    def test_org_owner_backstop_removes_without_being_a_team_member(self):
        """REGRESSION: indexing the hierarchy with the org owner's missing team role crashed (HTTP 500)."""
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        team = self.make_team(self.owner, org=org)
        member = self.add_team_member(team, self.make_user(), "LEAD").user
        self.assertOK(self.remove(org_owner, member, team))
        self.assertIsNone(self.role_of(member, team))

    def test_org_backstop_still_cannot_remove_the_creator(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        team = self.make_team(self.owner, org=org)
        self.assertDenied(self.remove(org_owner, self.owner, team))

    def test_unknown_email_is_404(self):
        resp = self.delete(self.owner, "remove-member", {"team_id": str(self.team.id), "email": "ghost@example.com"})
        self.assertOK(resp, 404)


class TeamSelfRemoveTests(TeamMemberTestBase):
    def leave(self, user):
        return self.delete(user, "self-remove-member", team_id=self.team.id)

    def test_off_by_default(self):
        self.assertDenied(self.leave(self.member))
        self.assertEqual(self.role_of(self.member), "MEMBER")

    def test_member_and_viewer_can_leave_when_allowed(self):
        self.set_settings(self.team, allow_self_removal=True)
        self.assertOK(self.leave(self.member))
        self.assertOK(self.leave(self.viewer))
        self.assertIsNone(self.role_of(self.member))

    def test_the_owner_cannot_leave(self):
        self.set_settings(self.team, allow_self_removal=True)
        self.assertDenied(self.leave(self.owner))

    def test_the_last_manager_cannot_leave(self):
        """REGRESSION: the last-manager check used `team.membership` (AttributeError -> HTTP 500)."""
        self.set_settings(self.team, allow_self_removal=True)
        self.assertDenied(self.leave(self.manager))
        self.assertEqual(self.role_of(self.manager), "MANAGER")

    def test_a_manager_can_leave_when_another_manager_remains(self):
        self.set_settings(self.team, allow_self_removal=True)
        self.add_team_member(self.team, self.make_user(), "MANAGER")
        self.assertOK(self.leave(self.manager))

    def test_outsider_is_refused(self):
        self.set_settings(self.team, allow_self_removal=True)
        self.assertDenied(self.leave(self.outsider))
