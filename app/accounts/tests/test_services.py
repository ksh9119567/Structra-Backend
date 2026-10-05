"""
Unit tests for the Redis-backed services: OTPs, reset tokens, the token registry
and invite tokens.
"""
import json

from django.test import SimpleTestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.testing.base import BaseAPITestCase
from services import otp_service, token_service
from services.invite_token_service import delete_invite_token, store_invite_token, verify_invite_token


class OTPServiceTests(BaseAPITestCase):
    def test_generate_otp_is_numeric_with_the_requested_length(self):
        for length in (4, 6, 8):
            otp = otp_service.generate_otp(length)
            self.assertEqual(len(otp), length)
            self.assertTrue(otp.isdigit())

    def test_generate_otp_defaults_to_six_digits(self):
        self.assertEqual(len(otp_service.generate_otp()), 6)

    def test_generate_otp_uses_a_cryptographic_source(self):
        # OTPs are credentials: they must come from `secrets`, not the predictable `random` module.
        import inspect
        source = inspect.getsource(otp_service.generate_otp)
        self.assertIn("secrets", source)
        self.assertNotIn("random.", source)

    def test_store_get_verify_roundtrip(self):
        otp_service.store_otp("login:email", "a@example.com", "123456")
        self.assertEqual(otp_service.get_otp("login:email", "a@example.com"), "123456")
        self.assertTrue(otp_service.verify_otp("login:email", "a@example.com", "123456"))

    def test_verify_consumes_the_code_only_on_success(self):
        otp_service.store_otp("login:email", "a@example.com", "123456")
        self.assertFalse(otp_service.verify_otp("login:email", "a@example.com", "000000"))
        self.assertEqual(otp_service.get_otp("login:email", "a@example.com"), "123456")   # still there
        self.assertTrue(otp_service.verify_otp("login:email", "a@example.com", "123456"))
        self.assertIsNone(otp_service.get_otp("login:email", "a@example.com"))             # consumed
        self.assertFalse(otp_service.verify_otp("login:email", "a@example.com", "123456"))

    def test_verify_without_a_stored_code(self):
        self.assertFalse(otp_service.verify_otp("login:email", "nobody@example.com", "123456"))

    def test_codes_expire(self):
        otp_service.store_otp("login:email", "a@example.com", "123456", ttl_seconds=10)
        self.redis().advance(11)
        self.assertIsNone(otp_service.get_otp("login:email", "a@example.com"))

    def test_attempt_counter_counts_and_resets_after_its_window(self):
        self.assertEqual([otp_service.increment_attempts("k", "id", 60) for _ in range(3)], [1, 2, 3])
        self.redis().advance(61)
        self.assertEqual(otp_service.increment_attempts("k", "id", 60), 1)

    def test_reset_attempts(self):
        otp_service.increment_attempts("k", "id", 60)
        otp_service.reset_attempts("k", "id")
        self.assertEqual(otp_service.increment_attempts("k", "id", 60), 1)

    def test_reset_token_lifecycle(self):
        token = otp_service.create_reset_token("user-1")
        self.assertEqual(len(token), 32)
        self.assertEqual(otp_service.get_userid_for_reset_token(token), "user-1")
        otp_service.delete_reset_token(token)
        self.assertIsNone(otp_service.get_userid_for_reset_token(token))
        self.assertIsNone(otp_service.get_userid_for_reset_token("unknown"))

    def test_reset_tokens_are_unique(self):
        self.assertNotEqual(otp_service.create_reset_token("u"), otp_service.create_reset_token("u"))


class TokenServiceTests(BaseAPITestCase):
    def test_refresh_token_registry(self):
        token_service.store_refresh_token("u1", "r-token", ttl=100)
        self.assertTrue(token_service.is_refresh_token_valid("r-token"))
        token_service.delete_refresh_token("r-token")
        self.assertFalse(token_service.is_refresh_token_valid("r-token"))

    def test_access_token_registry_expires_with_the_access_lifetime(self):
        token_service.store_access_token("u1", "a-token")
        self.assertTrue(token_service.is_access_token_valid("a-token"))
        self.assertAlmostEqual(self.redis().ttl("access:a-token"), 30 * 60, delta=3)
        self.redis().advance(30 * 60 + 1)
        self.assertFalse(token_service.is_access_token_valid("a-token"))

    def test_delete_access_token(self):
        token_service.store_access_token("u1", "a-token")
        token_service.delete_access_token("a-token")
        self.assertFalse(token_service.is_access_token_valid("a-token"))

    def test_refresh_token_defaults_to_the_configured_lifetime(self):
        token_service.store_refresh_token("u1", "r-token")
        self.assertAlmostEqual(self.redis().ttl("refresh:r-token"), 24 * 3600, delta=3)

    def test_unknown_tokens_are_invalid(self):
        self.assertFalse(token_service.is_refresh_token_valid("nope"))
        self.assertFalse(token_service.is_access_token_valid("nope"))


class InviteTokenServiceTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.invitee, self.other, self.inviter = self.make_user(), self.make_user(), self.make_user()
        self.project = self.make_project(self.inviter)

    def issue(self, role="VIEWER", invite_type="project"):
        return store_invite_token(user_id=self.invitee.id, invite_type=invite_type, invited_by=self.inviter.email,
                                  entity=self.project, role=role)

    def test_payload_roundtrip_and_single_use(self):
        token = self.issue("LEAD")
        payload = verify_invite_token(self.invitee, "project", token)
        self.assertEqual(payload["user_id"], str(self.invitee.id))
        self.assertEqual((payload["role"], payload["invite_type"], payload["entity_id"]),
                         ("LEAD", "project", str(self.project.id)))
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", token)      # consumed

    def test_another_user_is_forbidden_and_does_not_burn_the_token(self):
        """REGRESSION: PermissionDenied was swallowed and replaced by None."""
        token = self.issue()
        with self.assertRaises(PermissionDenied):
            verify_invite_token(self.other, "project", token)
        self.assertEqual(verify_invite_token(self.invitee, "project", token)["role"], "VIEWER")

    def test_unknown_expired_and_wrong_scope_tokens(self):
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", "nope")
        token = self.issue()
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "team", token)         # issued for a project
        self.redis().advance(24 * 3600 + 1)
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", token)

    def test_a_corrupt_stored_value_is_a_validation_error_not_none(self):
        self.redis().setex("invite_token:project:broken", 60, "{not json")
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", "broken")
        self.redis().setex("invite_token:project:partial", 60, json.dumps({"role": "VIEWER"}))
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", "partial")

    def test_delete_invite_token(self):
        token = self.issue()
        delete_invite_token("project", token)
        with self.assertRaises(ValidationError):
            verify_invite_token(self.invitee, "project", token)


class NoDatabaseSanityTests(SimpleTestCase):
    def test_token_prefixes_are_stable(self):
        # Other systems (and ops scripts) key off these - changing them logs everyone out.
        self.assertEqual(token_service.REDIS_KEY_PREFIX, "refresh:")
        self.assertEqual(token_service.REDIS_ACCESS_TOKEN_PREFIX, "access:")
        self.assertEqual(otp_service.REDIS_PREFIX, "otp:")
        self.assertEqual(otp_service.RESET_TOKEN_PREFIX, "password_reset_token:")
