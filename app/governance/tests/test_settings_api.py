"""
Settings endpoints: owners read and edit their container's governance rules;
nobody else can, and every threshold is validated against the system bounds.
"""
from urllib.parse import urlencode

from django.urls import resolve

from core.testing.base import API, BaseAPITestCase


def gurl(name, **query):
    url = f"{API}/governance/{name}/"
    return f"{url}?{urlencode(query)}" if query else url


class SettingsAPITestCase(BaseAPITestCase):
    def get(self, user, name, **query):
        return self.client_for(user).get(gurl(name, **query))

    def put(self, user, name, data=None, **query):
        return self.client_for(user).put(gurl(name, **query), data or {}, format="json")


class UrlNameTests(SettingsAPITestCase):
    def test_each_settings_url_has_its_own_name(self):
        """REGRESSION: all three GET urls were registered as 'get_org_settings'."""
        names = [resolve(f"{API}/governance/{p}/").url_name for p in
                 ("get-org-settings", "get-team-settings", "get-project-settings",
                  "update-org-settings", "update-team-settings", "update-project-settings")]
        self.assertEqual(len(set(names)), 6)


class OrgSettingsTests(SettingsAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)

    def update(self, user, **data):
        return self.put(user, "update-org-settings", data, org_id=self.org.id)

    def test_owner_reads_the_settings(self):
        resp = self.get(self.owner, "get-org-settings", org_id=self.org.id)
        self.assertOK(resp)
        data = resp.data["data"]
        self.assertEqual((data["max_members"], data["max_teams"], data["max_projects"]), (50, 5, 10))
        self.assertFalse(data["allow_member_invites"])
        self.assertEqual(data["invite_member_min_role"], "ADMIN")

    def test_owner_updates_flags_limits_and_thresholds(self):
        resp = self.update(self.owner, allow_member_invites=True, allow_team_creation=True, max_members=7,
                           invite_member_min_role="MANAGER", create_team_min_role="MANAGER")
        self.assertOK(resp)
        cfg = self.org.settings.__class__.objects.get(organization=self.org)
        self.assertEqual((cfg.allow_member_invites, cfg.allow_team_creation, cfg.max_members), (True, True, 7))
        self.assertEqual((cfg.invite_member_min_role, cfg.create_team_min_role), ("MANAGER", "MANAGER"))
        self.assertEqual(resp.data["data"]["max_members"], 7)

    def test_a_threshold_below_the_system_floor_is_rejected(self):
        resp = self.update(self.owner, invite_member_min_role="MEMBER")      # floor is MANAGER
        self.assertOK(resp, 400)
        self.assertIn("cannot be lower", str(resp.data))
        self.assertOK(self.update(self.owner, remove_member_min_role="MANAGER"), 400)   # fixed at ADMIN

    def test_a_threshold_above_the_system_ceiling_is_rejected(self):
        resp = self.update(self.owner, invite_member_min_role="OWNER")       # ceiling is ADMIN
        self.assertOK(resp, 400)
        self.assertIn("cannot be higher", str(resp.data))

    def test_an_unknown_role_is_rejected(self):
        self.assertOK(self.update(self.owner, invite_member_min_role="EMPEROR"), 400)

    def test_the_settings_row_cannot_be_re_pointed_at_another_org(self):
        """REGRESSION: `organization` was a writable field of the update serializer."""
        other = self.make_org(self.make_user())
        self.update(self.owner, organization=str(other.id), max_members=9)
        cfg = self.org.settings.__class__.objects.get(pk=self.org.settings.pk)
        self.assertEqual(cfg.organization_id, self.org.id)
        self.assertEqual(cfg.max_members, 9)

    def test_non_owners_cannot_read_or_write(self):
        for role in ("ADMIN", "MANAGER", "MEMBER", "VIEWER"):
            user = self.make_user()
            self.add_org_member(self.org, user, role)
            self.assertDenied(self.get(user, "get-org-settings", org_id=self.org.id))
            self.assertDenied(self.update(user, max_members=1))
        stranger = self.make_user()
        self.assertDenied(self.get(stranger, "get-org-settings", org_id=self.org.id))
        self.assertDenied(self.update(stranger, max_members=1))
        self.assertEqual(self.org.settings.__class__.objects.get(organization=self.org).max_members, 50)

    def test_unknown_missing_and_unauthenticated(self):
        self.assertOK(self.get(self.owner, "get-org-settings", org_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-org-settings"), 400)
        self.assertDenied(self.anon().get(gurl("get-org-settings", org_id=self.org.id)), 401)


class TeamSettingsTests(SettingsAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.team = self.make_team(self.owner)

    def update(self, user, **data):
        return self.put(user, "update-team-settings", data, team_id=self.team.id)

    def reload(self):
        return self.team.settings.__class__.objects.get(team=self.team)

    def test_owner_reads_the_settings(self):
        resp = self.get(self.owner, "get-team-settings", team_id=self.team.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["invite_member_min_role"], "MANAGER")
        self.assertEqual(resp.data["data"]["max_members"], 20)

    def test_owner_can_set_a_threshold_inside_the_band(self):
        self.assertOK(self.update(self.owner, invite_member_min_role="MANAGER", create_project_min_role="MANAGER"))

    def test_thresholds_outside_the_band_are_rejected(self):
        self.assertOK(self.update(self.owner, invite_member_min_role="LEAD"), 400)    # below: band is MANAGER..MANAGER
        self.assertOK(self.update(self.owner, invite_member_min_role="OWNER"), 400)   # above
        self.assertEqual(self.reload().invite_member_min_role, "MANAGER")

    def test_only_the_threshold_fields_are_editable_through_this_endpoint(self):
        self.update(self.owner, max_members=1, allow_member_invites=True, invite_member_min_role="MANAGER")
        cfg = self.reload()
        self.assertEqual(cfg.max_members, 20)
        self.assertFalse(cfg.allow_member_invites)

    def test_non_owners_cannot_read_or_write(self):
        for role in ("MANAGER", "LEAD", "MEMBER", "VIEWER"):
            user = self.make_user()
            self.add_team_member(self.team, user, role)
            self.assertDenied(self.get(user, "get-team-settings", team_id=self.team.id))
            self.assertDenied(self.update(user, invite_member_min_role="MANAGER"))
        self.assertDenied(self.get(self.make_user(), "get-team-settings", team_id=self.team.id))

    def test_unknown_missing_and_unauthenticated(self):
        self.assertOK(self.get(self.owner, "get-team-settings", team_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-team-settings"), 400)
        self.assertDenied(self.anon().get(gurl("get-team-settings", team_id=self.team.id)), 401)


class ProjectSettingsTests(SettingsAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)

    def update(self, user, **data):
        return self.put(user, "update-project-settings", data, project_id=self.project.id)

    def reload(self):
        return self.project.settings.__class__.objects.get(project=self.project)

    def test_owner_reads_the_settings(self):
        resp = self.get(self.owner, "get-project-settings", project_id=self.project.id)
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["create_task_min_role"], "MANAGER")
        self.assertTrue(resp.data["data"]["allow_task_creation"])

    def test_owner_lowers_the_task_thresholds_within_the_band(self):
        resp = self.update(self.owner, create_task_min_role="CONTRIBUTOR", update_task_min_role="LEAD",
                           invite_member_min_role="LEAD")
        self.assertOK(resp)
        cfg = self.reload()
        self.assertEqual((cfg.create_task_min_role, cfg.update_task_min_role, cfg.invite_member_min_role),
                         ("CONTRIBUTOR", "LEAD", "LEAD"))

    def test_thresholds_outside_the_band_are_rejected(self):
        self.assertOK(self.update(self.owner, create_task_min_role="VIEWER"), 400)      # floor CONTRIBUTOR
        self.assertOK(self.update(self.owner, create_task_min_role="OWNER"), 400)       # ceiling MANAGER
        self.assertOK(self.update(self.owner, invite_member_min_role="CONTRIBUTOR"), 400)   # floor LEAD
        self.assertOK(self.update(self.owner, delete_task_min_role="LEAD"), 400)        # fixed at MANAGER
        self.assertEqual(self.reload().create_task_min_role, "MANAGER")

    def test_only_the_threshold_fields_are_editable_through_this_endpoint(self):
        self.update(self.owner, max_members=1, allow_task_creation=False, create_task_min_role="LEAD")
        cfg = self.reload()
        self.assertEqual(cfg.max_members, 20)
        self.assertTrue(cfg.allow_task_creation)

    def test_non_owners_cannot_read_or_write(self):
        for role in ("MANAGER", "LEAD", "CONTRIBUTOR", "VIEWER"):
            user = self.make_user()
            self.add_project_member(self.project, user, role)
            self.assertDenied(self.get(user, "get-project-settings", project_id=self.project.id))
            self.assertDenied(self.update(user, create_task_min_role="LEAD"))
        self.assertDenied(self.get(self.make_user(), "get-project-settings", project_id=self.project.id))

    def test_unknown_missing_and_unauthenticated(self):
        self.assertOK(self.get(self.owner, "get-project-settings", project_id="00000000-0000-0000-0000-000000000000"), 404)
        self.assertOK(self.get(self.owner, "get-project-settings"), 400)
        self.assertDenied(self.anon().get(gurl("get-project-settings", project_id=self.project.id)), 401)

    def test_changed_thresholds_take_effect_on_the_task_api(self):
        contributor = self.make_user()
        self.add_project_member(self.project, contributor, "CONTRIBUTOR")
        body = {"title": "x", "project_id": str(self.project.id)}
        client = self.client_for(contributor)
        self.assertDenied(client.post(f"{API}/tasks/create-task/", body, format="json"))
        self.assertOK(self.update(self.owner, create_task_min_role="CONTRIBUTOR"))
        self.assertOK(client.post(f"{API}/tasks/create-task/", body, format="json"), 201)
