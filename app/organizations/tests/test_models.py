from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from app.governance.models import OrganizationSettings
from app.organizations.models import Organization, OrganizationMembership
from core.testing.base import BaseAPITestCase


class OrganizationModelTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.org = self.make_org(self.owner, name="Acme")

    def test_str(self):
        self.assertEqual(str(self.org), "Acme")
        membership = OrganizationMembership.objects.get(organization=self.org, user=self.owner)
        self.assertEqual(str(membership), f"{self.owner.email} - Acme")

    def test_settings_row_is_created_automatically_with_safe_defaults(self):
        cfg = OrganizationSettings.objects.get(organization=self.org)
        self.assertEqual((cfg.max_members, cfg.max_teams, cfg.max_projects), (50, 5, 10))
        self.assertFalse(cfg.allow_member_invites)
        self.assertFalse(cfg.allow_team_creation)
        self.assertFalse(cfg.allow_project_creation)
        self.assertEqual(cfg.default_member_role, "MEMBER")

    def test_membership_is_unique_per_user_and_org(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="VIEWER")

    def test_membership_role_defaults_from_org_settings(self):
        membership = OrganizationMembership(organization=self.org, user=self.make_user(), role="")
        membership.save()
        self.assertEqual(membership.role, "MEMBER")

    def test_the_owner_user_cannot_be_deleted_while_owning_an_org(self):
        with self.assertRaises(ProtectedError):
            self.owner.delete()

    def test_deleting_an_org_cascades(self):
        self.org.delete()
        self.assertEqual(OrganizationMembership.objects.count(), 0)
        self.assertEqual(OrganizationSettings.objects.count(), 0)

    def test_soft_delete_flag_defaults_false(self):
        self.assertFalse(Organization.objects.get(pk=self.org.pk).is_deleted)
