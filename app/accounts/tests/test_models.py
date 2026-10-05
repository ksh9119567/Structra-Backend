import uuid

from django.test import TestCase

from app.accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_hashes_the_password_and_normalises_the_email(self):
        user = User.objects.create_user(email="Jane@EXAMPLE.com", password="s3cret-pass")
        self.assertEqual(user.email, "Jane@example.com")  # domain part lower-cased
        self.assertNotEqual(user.password, "s3cret-pass")
        self.assertTrue(user.check_password("s3cret-pass"))

    def test_defaults(self):
        user = User.objects.create_user(email="a@example.com", password="x-pass-1")
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_deleted)
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)
        self.assertIsNone(user.phone_no)

    def test_email_and_password_are_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x-pass-1")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="a@example.com", password=None)

    def test_email_is_unique(self):
        from django.db import IntegrityError, transaction
        User.objects.create_user(email="a@example.com", password="x-pass-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@example.com", password="x-pass-2")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="root@example.com", password="x-pass-1")
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.is_active)

    def test_superuser_needs_a_password_and_the_right_flags(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="root@example.com", password=None)
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="root@example.com", password="x-pass-1", is_staff=False)
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="root@example.com", password="x-pass-1", is_superuser=False)

    def test_str_and_phone_alias(self):
        user = User.objects.create_user(email="a@example.com", password="x-pass-1", phone_no="+15551234567")
        self.assertEqual(str(user), "a@example.com")
        self.assertEqual(user.phone_number, "+15551234567")

    def test_login_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
