"""
The get_* lookup helpers and add_member(): wrong ids must become 4xx errors, never HTTP 500.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from core.testing.base import BaseAPITestCase
from core.utils.base_utils import add_member, get_user
from core.utils.org_utils import get_all_org_memberships, get_org, get_org_membership
from core.utils.project_utils import get_all_project_memberships, get_project, get_project_membership
from core.utils.task_utils import get_all_task, get_task
from core.utils.team_utils import get_all_team_memberships, get_team, get_team_membership

MISSING = "00000000-0000-0000-0000-000000000000"


class EntityLookupTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner)
        self.team = self.make_team(self.owner)
        self.project = self.make_project(self.owner)
        self.task = self.project.tasks.create(title="t", created_by=self.owner)
        self.lookups = {
            "org": (get_org, self.org),
            "team": (get_team, self.team),
            "project": (get_project, self.project),
            "task": (get_task, self.task),
        }

    def test_found(self):
        for name, (getter, obj) in self.lookups.items():
            self.assertEqual(getter(obj.id), obj, name)
            self.assertEqual(getter(str(obj.id)), obj, name)

    def test_missing_is_not_found(self):
        for name, (getter, _obj) in self.lookups.items():
            with self.assertRaises(NotFound, msg=name):
                getter(MISSING)

    def test_malformed_id_is_not_found_not_a_crash(self):
        for name, (getter, _obj) in self.lookups.items():
            with self.assertRaises(NotFound, msg=name):
                getter("not-a-uuid")

    def test_soft_deleted_is_not_found(self):
        for name, (getter, obj) in self.lookups.items():
            obj.is_deleted = True
            obj.save()
            with self.assertRaises(NotFound, msg=name):
                getter(obj.id)

    def test_empty_id_is_a_validation_error(self):
        for name, (getter, _obj) in self.lookups.items():
            for empty in (None, ""):
                with self.assertRaises(ValidationError, msg=f"{name}/{empty!r}"):
                    getter(empty)

    def test_error_messages_name_the_entity(self):
        for name, (getter, _obj) in self.lookups.items():
            with self.assertRaises(NotFound) as ctx:
                getter(MISSING)
            self.assertIn(name, str(ctx.exception.detail).lower())

    def test_get_all_task_is_live_and_stably_ordered(self):
        later = self.project.tasks.create(title="later", created_by=self.owner)
        gone = self.project.tasks.create(title="gone", created_by=self.owner, is_deleted=True)
        # pin the timestamps - two inserts can land in the same clock tick on Windows
        base = timezone.now()
        for offset, task in enumerate((self.task, later, gone)):
            self.project.tasks.filter(pk=task.pk).update(created_at=base + timedelta(seconds=offset))
        qs = get_all_task(self.project)
        self.assertEqual([t.id for t in qs], [self.task.id, later.id])
        self.assertNotIn(gone, qs)
        self.assertTrue(qs.ordered)
        with self.assertRaises(ValidationError):
            get_all_task(None)


class MembershipLookupTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner, self.stranger = self.make_user(), self.make_user()
        self.org = self.make_org(self.owner)
        self.team = self.make_team(self.owner)
        self.project = self.make_project(self.owner)

    def test_found(self):
        self.assertEqual(get_org_membership(self.org.id, self.owner).role, "OWNER")
        self.assertEqual(get_team_membership(self.team.id, self.owner).role, "OWNER")
        self.assertEqual(get_project_membership(self.project.id, self.owner).role, "OWNER")

    def test_a_non_member_is_not_found(self):
        """REGRESSION: get_project_membership() raised a bare Exception (HTTP 500)."""
        with self.assertRaises(NotFound):
            get_org_membership(self.org.id, self.stranger)
        with self.assertRaises(NotFound):
            get_team_membership(self.team.id, self.stranger)
        with self.assertRaises(NotFound):
            get_project_membership(self.project.id, self.stranger)

    def test_missing_arguments_are_validation_errors(self):
        for getter in (get_org_membership, get_team_membership, get_project_membership):
            with self.assertRaises(ValidationError):
                getter(None, self.owner)
            with self.assertRaises(ValidationError):
                getter(self.org.id, None)

    def test_listing_helpers(self):
        self.assertEqual(get_all_org_memberships(self.org.id).count(), 1)
        self.assertEqual(get_all_team_memberships(self.team.id).count(), 1)
        self.assertEqual(get_all_project_memberships(self.project.id).count(), 1)
        for getter in (get_all_org_memberships, get_all_team_memberships, get_all_project_memberships):
            with self.assertRaises(ValidationError):
                getter(None)


class GetUserTests(BaseAPITestCase):
    def test_email_lookup_is_case_insensitive(self):
        user = self.make_user(email="Mixed@Example.com")
        self.assertEqual(get_user("mixed@example.com"), user)
        self.assertEqual(get_user("MIXED@EXAMPLE.COM", kind="email"), user)

    def test_phone_lookup(self):
        user = self.make_user(phone_no="+15551234567")
        self.assertEqual(get_user("+15551234567", kind="phone"), user)

    def test_unknown_and_soft_deleted_users_are_none(self):
        self.assertIsNone(get_user("ghost@example.com"))
        user = self.make_user(email="gone@example.com")
        user.is_deleted = True
        user.save()
        self.assertIsNone(get_user("gone@example.com"))

    def test_empty_identifier_is_a_validation_error(self):
        with self.assertRaises(ValidationError):
            get_user("")


class AddMemberTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner, self.user = self.make_user(), self.make_user()
        self.org = self.make_org(self.owner)
        self.team = self.make_team(self.owner)
        self.project = self.make_project(self.owner)

    def payload(self, invite_type, entity, role="VIEWER", user=None):
        return {"entity_id": str(entity.id), "user_id": str((user or self.user).id), "role": role, "invite_type": invite_type}

    def test_adds_to_each_scope(self):
        self.assertEqual(add_member(self.payload("organization", self.org)).organization, self.org)
        self.assertEqual(add_member(self.payload("team", self.team)).team, self.team)
        self.assertEqual(add_member(self.payload("project", self.project)).project, self.project)

    def test_already_a_member_stays_a_validation_error(self):
        """REGRESSION: it used to be re-wrapped in a bare Exception (HTTP 500)."""
        add_member(self.payload("project", self.project))
        with self.assertRaises(ValidationError):
            add_member(self.payload("project", self.project))

    def test_unknown_invite_type(self):
        with self.assertRaises(ValidationError):
            add_member(self.payload("galaxy", self.project))

    def test_unknown_or_deleted_user_is_not_found(self):
        gone = self.make_user()
        gone.is_deleted = True
        gone.save()
        with self.assertRaises(NotFound):
            add_member(self.payload("team", self.team, user=gone))
        bad = self.payload("team", self.team)
        bad["user_id"] = MISSING
        with self.assertRaises(NotFound):
            add_member(bad)

    def test_unknown_entity_is_not_found(self):
        payload = self.payload("team", self.team)
        payload["entity_id"] = MISSING
        with self.assertRaises(NotFound):
            add_member(payload)
