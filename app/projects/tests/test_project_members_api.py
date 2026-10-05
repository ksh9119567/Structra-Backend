"""
Project membership endpoints: members list, invites (+ role-escalation guard),
accept-invite, update-member, remove-member, self-remove, stale-members.
"""
from django.core import mail

from app.projects.models import Project, ProjectMembership
from app.projects.services.project_team_service import assign_team
from .helpers import ProjectAPITestCase, purl, results


class MemberTestBase(ProjectAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)
        self.manager = self.make_user()
        self.lead = self.make_user()
        self.contributor = self.make_user()
        self.viewer = self.make_user()
        self.add_project_member(self.project, self.manager, "MANAGER")
        self.add_project_member(self.project, self.lead, "LEAD")
        self.add_project_member(self.project, self.contributor, "CONTRIBUTOR")
        self.add_project_member(self.project, self.viewer, "VIEWER")
        self.outsider = self.make_user()

    def role_of(self, user, project=None):
        m = ProjectMembership.objects.filter(project=project or self.project, user=user).first()
        return m.role if m else None


class ProjectMembersListTests(MemberTestBase):
    def test_any_member_can_list_members(self):
        resp = self.get(self.viewer, "get-project-members", project_id=self.project.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["count"], 5)
        self.assertEqual({m["user_email"] for m in results(resp)},
                         {u.email for u in (self.owner, self.manager, self.lead, self.contributor, self.viewer)})

    def test_filter_by_role_and_search(self):
        resp = self.get(self.owner, "get-project-members", project_id=self.project.id, role="LEAD")
        self.assertEqual([m["user_email"] for m in results(resp)], [self.lead.email])
        resp = self.get(self.owner, "get-project-members", project_id=self.project.id, search=self.manager.email)
        self.assertEqual([m["user_email"] for m in results(resp)], [self.manager.email])

    def test_outsider_is_refused(self):
        self.assertDenied(self.get(self.outsider, "get-project-members", project_id=self.project.id))

    def test_org_member_may_list_members_of_an_org_project(self):
        org = self.make_org(self.make_user())
        project = self.make_project(self.owner, org=org)
        member = self.make_user()
        self.add_org_member(org, member, "VIEWER")
        self.assertOK(self.get(member, "get-project-members", project_id=project.id))

    def test_unknown_project_is_404(self):
        self.assertOK(self.get(self.owner, "get-project-members", project_id="00000000-0000-0000-0000-000000000000"), 404)


class ProjectInviteTests(MemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()

    def invite(self, actor, email=None, role=None, project=None):
        data = {"email": (email or self.invitee.email)}
        if role:
            data["role"] = role
        return self.post(actor, "send-invite", data, project_id=(project or self.project).id)

    # ---- who may invite ----
    def test_owner_invites_and_the_token_and_email_are_issued(self):
        resp = self.invite(self.owner)
        self.assertOK(resp)
        token = resp.data["invite_token"]
        self.assertEqual(self.redis().exists(f"invite_token:project:{token}"), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.invitee.email])

    def test_default_role_is_contributor(self):
        token = self.invite(self.owner).data["invite_token"]
        self.assertOK(self.post(self.invitee, "accept-project-invite", invite_token=token))
        self.assertEqual(self.role_of(self.invitee), "CONTRIBUTOR")

    def test_manager_is_blocked_until_the_project_allows_member_invites(self):
        resp = self.invite(self.manager)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to invite", str(resp.data))
        self.set_settings(self.project, allow_member_invites=True)
        self.assertOK(self.invite(self.manager))

    def test_lead_needs_both_the_flag_and_a_lowered_threshold(self):
        self.set_settings(self.project, allow_member_invites=True)  # threshold still MANAGER
        resp = self.invite(self.lead)
        self.assertOK(resp, 400)
        self.assertIn("MANAGER", str(resp.data))
        self.set_settings(self.project, invite_member_min_role="LEAD")
        self.assertOK(self.invite(self.lead, role="CONTRIBUTOR"))

    def test_threshold_below_the_system_floor_is_clamped_to_lead(self):
        self.set_settings(self.project, allow_member_invites=True, invite_member_min_role="VIEWER")
        self.assertDenied(self.invite(self.contributor))               # structural gate: LEAD+
        self.assertOK(self.invite(self.lead, role="VIEWER"))            # clamped to LEAD -> lead passes

    def test_contributor_viewer_and_outsider_cannot_invite(self):
        for user in (self.contributor, self.viewer, self.outsider):
            self.assertDenied(self.invite(user))

    def test_org_owner_backstop_invites_without_being_a_member_and_bypasses_the_policy(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        self.assertEqual(project.settings.allow_member_invites, False)
        self.assertOK(self.invite(org_owner, project=project))

    def test_requires_authentication(self):
        resp = self.anon().post(purl("send-invite", project_id=self.project.id), {"email": self.invitee.email}, format="json")
        self.assertDenied(resp, 401)

    # ---- role-escalation guard ----
    def test_nobody_can_invite_straight_in_as_owner(self):
        self.set_settings(self.project, allow_member_invites=True)
        for actor in (self.owner, self.manager):
            resp = self.invite(actor, role="OWNER")
            self.assertOK(resp, 400)
            self.assertIn("Ownership", str(resp.data))

    def test_manager_cannot_invite_an_equal_role(self):
        self.set_settings(self.project, allow_member_invites=True)
        self.assertOK(self.invite(self.manager, role="MANAGER"), 400)

    def test_manager_can_invite_below_their_own_role(self):
        self.set_settings(self.project, allow_member_invites=True)
        for role in ("LEAD", "CONTRIBUTOR", "VIEWER", "GUEST"):
            self.assertOK(self.invite(self.manager, email=self.make_user().email, role=role))

    def test_lead_cannot_invite_an_equal_or_higher_role(self):
        self.set_settings(self.project, allow_member_invites=True, invite_member_min_role="LEAD")
        self.assertOK(self.invite(self.lead, role="LEAD"), 400)
        self.assertOK(self.invite(self.lead, role="MANAGER"), 400)

    def test_owner_can_invite_a_manager(self):
        self.assertOK(self.invite(self.owner, role="MANAGER"))

    def test_invalid_role_is_rejected(self):
        self.assertOK(self.invite(self.owner, role="BOSS"), 400)

    # ---- validation ----
    def test_unknown_user_is_404(self):
        self.assertOK(self.invite(self.owner, email="ghost@example.com"), 404)

    def test_cannot_invite_yourself(self):
        self.assertOK(self.invite(self.owner, email=self.owner.email), 400)

    def test_cannot_invite_an_existing_member(self):
        self.assertOK(self.invite(self.owner, email=self.viewer.email), 400)

    def test_invalid_email_is_rejected(self):
        self.assertOK(self.invite(self.owner, email="not-an-email"), 400)

    def test_member_limit_counts_explicit_members(self):
        self.set_settings(self.project, max_members=5)  # already 5 explicit members
        self.assertOK(self.invite(self.owner), 400)
        self.set_settings(self.project, max_members=6)
        self.assertOK(self.invite(self.owner))

    def test_a_big_assigned_team_does_not_use_up_member_slots(self):
        team = self.make_team(self.make_user())
        for _ in range(10):
            self.add_team_member(team, self.make_user())
        assign_team(project=self.project, team=team, role="CONTRIBUTOR", is_owning=True, assigned_by=self.owner)
        self.set_settings(self.project, max_members=6)
        self.assertOK(self.invite(self.owner))


class ProjectAcceptInviteTests(MemberTestBase):
    def setUp(self):
        super().setUp()
        self.invitee = self.make_user()
        resp = self.post(self.owner, "send-invite", {"email": self.invitee.email, "role": "LEAD"}, project_id=self.project.id)
        self.token = resp.data["invite_token"]

    def accept(self, user, token=None):
        return self.post(user, "accept-project-invite", invite_token=token or self.token)

    def test_invitee_joins_with_the_invited_role(self):
        resp = self.accept(self.invitee)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["role"], "LEAD")
        self.assertEqual(self.role_of(self.invitee), "LEAD")

    def test_token_is_single_use(self):
        self.assertOK(self.accept(self.invitee))
        self.assertOK(self.accept(self.invitee), 400)

    def test_someone_elses_token_is_403_and_stays_usable(self):
        """REGRESSION: used to surface as HTTP 500 and was silently swallowed."""
        self.assertOK(self.accept(self.outsider), 403)
        self.assertIsNone(self.role_of(self.outsider))
        self.assertOK(self.accept(self.invitee))  # the rightful invitee can still use it

    def test_unknown_missing_and_expired_tokens(self):
        self.assertOK(self.accept(self.invitee, token="deadbeef"), 400)
        self.assertOK(self.post(self.invitee, "accept-project-invite"), 400)
        self.redis().advance(24 * 3600 + 1)
        self.assertOK(self.accept(self.invitee), 400)

    def test_already_a_member_is_400_not_500(self):
        """REGRESSION: add_member() re-wrapped DRF errors in a bare Exception."""
        self.add_project_member(self.project, self.invitee, "VIEWER")
        self.assertOK(self.accept(self.invitee), 400)
        self.assertEqual(self.role_of(self.invitee), "VIEWER")

    def test_project_deleted_before_accepting_is_404(self):
        self.project.is_deleted = True
        self.project.save()
        self.assertOK(self.accept(self.invitee), 404)

    def test_requires_authentication(self):
        resp = self.anon().post(purl("accept-project-invite", invite_token=self.token))
        self.assertDenied(resp, 401)


class ProjectUpdateMemberTests(MemberTestBase):
    def update(self, actor, target, role, project=None):
        return self.put(actor, "update-member", {"email": target.email, "role": role}, project_id=(project or self.project).id)

    def test_owner_changes_a_role(self):
        self.assertOK(self.update(self.owner, self.contributor, "LEAD"))
        self.assertEqual(self.role_of(self.contributor), "LEAD")

    def test_manager_is_blocked_until_the_project_allows_member_updates(self):
        resp = self.update(self.manager, self.contributor, "LEAD")
        self.assertOK(resp, 400)
        self.assertIn("not allowed to update", str(resp.data))
        self.set_settings(self.project, allow_member_updates=True)
        self.assertOK(self.update(self.manager, self.contributor, "LEAD"))

    def test_manager_cannot_grant_an_equal_or_higher_role(self):
        self.set_settings(self.project, allow_member_updates=True)
        self.assertOK(self.update(self.manager, self.contributor, "MANAGER"), 400)
        self.assertOK(self.update(self.manager, self.contributor, "OWNER"), 400)
        self.assertEqual(self.role_of(self.contributor), "CONTRIBUTOR")

    def test_manager_cannot_touch_an_equal_or_higher_member(self):
        self.set_settings(self.project, allow_member_updates=True)
        other_manager = self.make_user()
        self.add_project_member(self.project, other_manager, "MANAGER")
        self.assertOK(self.update(self.manager, other_manager, "VIEWER"), 400)
        self.assertOK(self.update(self.manager, self.owner, "VIEWER"), 400)

    def test_lead_contributor_and_outsider_cannot_update(self):
        for user in (self.lead, self.contributor, self.outsider):
            self.assertDenied(self.update(user, self.viewer, "CONTRIBUTOR"))

    def test_the_last_manager_cannot_be_downgraded(self):
        resp = self.update(self.owner, self.manager, "LEAD")
        self.assertOK(resp, 400)
        self.assertIn("last remaining Manager", str(resp.data))

    def test_a_team_derived_participant_can_be_elevated_to_explicit_member(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.assertIsNone(self.role_of(member))
        resp = self.update(self.owner, member, "LEAD")
        self.assertOK(resp)
        self.assertEqual(self.role_of(member), "LEAD")

    def test_org_owner_backstop_can_update_members_without_being_one(self):
        """REGRESSION: the view bypassed the policy gate but the serializer rejected a non-member."""
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        member = self.make_user()
        self.add_project_member(project, member, "CONTRIBUTOR")
        self.assertOK(self.update(org_owner, member, "LEAD", project))
        self.assertEqual(self.role_of(member, project), "LEAD")

    def test_backstop_still_cannot_mint_an_owner_or_demote_the_owner(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        member = self.make_user()
        self.add_project_member(project, member, "CONTRIBUTOR")
        self.assertOK(self.update(org_owner, member, "OWNER", project), 400)
        self.assertOK(self.update(org_owner, self.owner, "VIEWER", project), 400)

    def test_bad_input(self):
        self.assertOK(self.update(self.owner, self.contributor, "BOSS"), 400)
        resp = self.put(self.owner, "update-member", {"email": self.contributor.email}, project_id=self.project.id)
        self.assertOK(resp, 400)
        self.assertOK(self.put(self.owner, "update-member", {"email": "ghost@example.com", "role": "LEAD"},
                               project_id=self.project.id), 404)


class ProjectRemoveMemberTests(MemberTestBase):
    def remove(self, actor, target, project=None):
        return self.delete(actor, "remove-member", {"email": target.email}, project_id=(project or self.project).id)

    def test_owner_removes_members_of_any_lower_rank(self):
        for user in (self.contributor, self.viewer, self.lead):
            self.assertOK(self.remove(self.owner, user))
            self.assertIsNone(self.role_of(user))

    def test_manager_is_blocked_until_the_project_allows_removal(self):
        resp = self.remove(self.manager, self.contributor)
        self.assertOK(resp, 400)
        self.assertIn("not allowed to remove", str(resp.data))
        self.set_settings(self.project, allow_member_removal=True)
        self.assertOK(self.remove(self.manager, self.contributor))

    def test_manager_cannot_remove_an_equal_or_higher_member(self):
        self.set_settings(self.project, allow_member_removal=True)
        other_manager = self.make_user()
        self.add_project_member(self.project, other_manager, "MANAGER")
        self.assertDenied(self.remove(self.manager, other_manager))

    def test_the_creator_can_never_be_removed(self):
        self.set_settings(self.project, allow_member_removal=True)
        self.assertDenied(self.remove(self.manager, self.owner))

    def test_lead_contributor_and_outsider_cannot_remove(self):
        for user in (self.lead, self.contributor, self.outsider):
            self.assertDenied(self.remove(user, self.viewer))

    def test_the_last_manager_cannot_be_removed(self):
        resp = self.remove(self.owner, self.manager)
        self.assertDenied(resp)
        self.assertIn("Last manager", str(resp.data))

    def test_a_non_member_is_a_clean_400(self):
        self.assertOK(self.remove(self.owner, self.outsider), 400)

    def test_team_derived_participant_must_be_removed_from_the_team(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        resp = self.remove(self.owner, member)
        self.assertOK(resp, 400)
        self.assertIn("team", str(resp.data).lower())

    def test_org_owner_backstop_can_remove_members_without_being_one(self):
        """REGRESSION: the backstop passed the permission class, then the rank check threw them out."""
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        member = self.make_user()
        self.add_project_member(project, member, "LEAD")
        self.assertOK(self.remove(org_owner, member, project))
        self.assertIsNone(self.role_of(member, project))

    def test_backstop_cannot_remove_the_creator(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        self.assertDenied(self.remove(org_owner, self.owner, project))

    def test_unknown_email_is_404(self):
        resp = self.delete(self.owner, "remove-member", {"email": "ghost@example.com"}, project_id=self.project.id)
        self.assertOK(resp, 404)


class ProjectSelfRemoveTests(MemberTestBase):
    def leave(self, user):
        return self.delete(user, "self-remove-member", project_id=self.project.id)

    def test_self_removal_is_off_by_default(self):
        resp = self.leave(self.contributor)
        self.assertDenied(resp)
        self.assertEqual(self.role_of(self.contributor), "CONTRIBUTOR")

    def test_member_can_leave_when_allowed(self):
        self.set_settings(self.project, allow_self_removal=True)
        self.assertOK(self.leave(self.contributor))
        self.assertIsNone(self.role_of(self.contributor))

    def test_the_owner_cannot_leave(self):
        self.set_settings(self.project, allow_self_removal=True)
        self.assertDenied(self.leave(self.owner))

    def test_the_last_manager_cannot_leave(self):
        self.set_settings(self.project, allow_self_removal=True)
        self.assertDenied(self.leave(self.manager))

    def test_team_derived_participant_is_told_to_leave_the_team_instead(self):
        team = self.make_team(self.make_user())
        member = self.make_user()
        self.add_team_member(team, member)
        assign_team(project=self.project, team=team, role="VIEWER", is_owning=True, assigned_by=self.owner)
        self.set_settings(self.project, allow_self_removal=True)
        self.assertOK(self.leave(member), 400)

    def test_outsider_is_refused(self):
        self.set_settings(self.project, allow_self_removal=True)
        self.assertDenied(self.leave(self.outsider))


class ProjectStaleMembersTests(MemberTestBase):
    def test_lists_explicit_members_who_left_the_org(self):
        org_owner = self.make_user()
        org = self.make_org(org_owner)
        project = self.make_project(self.owner, org=org)
        stays, drifted = self.make_user(), self.make_user()
        self.add_org_member(org, stays, "MEMBER")
        self.add_project_member(project, stays, "CONTRIBUTOR")
        self.add_project_member(project, drifted, "CONTRIBUTOR")  # was never in / has left the org
        manager = self.make_user()
        self.add_org_member(org, manager, "MEMBER")
        self.add_project_member(project, manager, "MANAGER")

        resp = self.get(manager, "get-stale-members", project_id=project.id)
        self.assertOK(resp)
        self.assertEqual({m["user_email"] for m in results(resp)}, {drifted.email})

    def test_empty_for_a_project_with_no_container(self):
        self.assertEqual(results(self.get(self.owner, "get-stale-members", project_id=self.project.id)), [])

    def test_only_managers_and_up_can_view_the_report(self):
        for user in (self.lead, self.contributor, self.viewer, self.outsider):
            self.assertDenied(self.get(user, "get-stale-members", project_id=self.project.id))
        self.assertOK(self.get(self.manager, "get-stale-members", project_id=self.project.id))
