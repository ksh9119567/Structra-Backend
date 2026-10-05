"""
Registration, login, token refresh, logout and the JWT + Redis session check.
"""
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from app.accounts.models import User
from .helpers import AccountAPITestCase, aurl, lifetime_seconds

DAY = 24 * 3600


class RegisterTests(AccountAPITestCase):
    def register(self, **overrides):
        return self.anon().post(aurl("register"), self.register_payload(**overrides), format="json")

    def test_creates_the_user_and_returns_working_tokens(self):
        payload = self.register_payload(email="neo@example.com", phone_number="+15551234567")
        resp = self.anon().post(aurl("register"), payload, format="json")
        self.assertOK(resp, 201)
        self.assertEqual(resp.data["user"]["email"], "neo@example.com")
        self.assertNotIn("password", resp.data["user"])
        user = User.objects.get(email="neo@example.com")
        self.assertTrue(user.check_password(self.PASSWORD))
        self.assertEqual(user.phone_no, "+15551234567")
        self.assertFalse(user.is_email_verified)        # only OTP verification flips this
        # the returned access token is registered and usable straight away
        client = self.anon()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        self.assertOK(client.get(aurl("get-user")))
        self.assertEqual(self.redis().exists(f"refresh:{resp.data['refresh']}"), 1)

    def test_phone_is_optional(self):
        self.assertOK(self.register(), 201)
        self.assertOK(self.register(phone_number=""), 201)
        self.assertOK(self.register(phone_number=""), 201)   # several users may have no phone

    def test_duplicate_email_is_rejected(self):
        self.assertOK(self.register(email="dup@example.com"), 201)
        self.assertOK(self.register(email="dup@example.com"), 400)

    def test_duplicate_email_is_rejected_ignoring_case(self):
        """REGRESSION: A@x.com and a@x.com were both accepted, but every lookup is case-insensitive."""
        self.assertOK(self.register(email="case@example.com"), 201)
        self.assertOK(self.register(email="CASE@example.com"), 400)
        self.assertEqual(User.objects.filter(email__iexact="case@example.com").count(), 1)

    def test_duplicate_phone_is_rejected(self):
        """REGRESSION: duplicates made phone-based OTP / reset lookups ambiguous (HTTP 500)."""
        self.assertOK(self.register(phone_number="+15551234567"), 201)
        self.assertOK(self.register(phone_number="+15551234567"), 400)

    def test_validation(self):
        self.assertOK(self.register(email=""), 400)
        self.assertOK(self.register(email="not-an-email"), 400)
        self.assertOK(self.register(password=""), 400)
        self.assertOK(self.register(password="12345"), 400)           # min length 6
        payload = self.register_payload()
        del payload["email"]
        self.assertOK(self.anon().post(aurl("register"), payload, format="json"), 400)

    def test_cannot_self_assign_staff_or_verification_flags(self):
        resp = self.register(email="sneaky@example.com", is_staff=True, is_superuser=True, is_email_verified=True)
        self.assertOK(resp, 201)
        user = User.objects.get(email="sneaky@example.com")
        self.assertFalse(user.is_staff or user.is_superuser or user.is_email_verified)

    def test_get_method_not_allowed(self):
        self.assertOK(self.anon().get(aurl("register")), 405)


class LoginTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="login@example.com")

    def test_success_returns_tokens_registered_in_redis(self):
        resp = self.login("login@example.com")
        self.assertOK(resp)
        self.assertEqual(self.redis().exists(f"refresh:{resp.data['refresh']}"), 1)
        self.assertEqual(self.redis().exists(f"access:{resp.data['access']}"), 1)
        self.assertEqual(AccessToken(resp.data["access"])["email"], "login@example.com")

    def test_wrong_password_and_unknown_email_are_401(self):
        self.assertOK(self.login("login@example.com", password="wrong-pass"), 401)
        self.assertOK(self.login("ghost@example.com"), 401)

    def test_missing_fields_are_400(self):
        self.assertOK(self.anon().post(aurl("login"), {"email": "login@example.com"}, format="json"), 400)
        self.assertOK(self.anon().post(aurl("login"), {}, format="json"), 400)

    def test_inactive_and_soft_deleted_accounts_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        self.assertOK(self.login("login@example.com"), 401)
        self.user.is_active, self.user.is_deleted = False, True
        self.user.save()
        self.assertOK(self.login("login@example.com"), 401)

    def test_default_session_is_one_day_and_remember_me_is_thirty(self):
        short = self.login("login@example.com")
        self.assertAlmostEqual(lifetime_seconds(short.data["refresh"]), DAY, delta=10)
        long = self.login("login@example.com", remember_me=True)
        self.assertAlmostEqual(lifetime_seconds(long.data["refresh"]), 30 * DAY, delta=10)
        self.assertTrue(RefreshToken(long.data["refresh"])["remember_me"])
        self.assertFalse(RefreshToken(short.data["refresh"])["remember_me"])

    def test_refresh_ttl_in_redis_matches_the_token_lifetime(self):
        long = self.login("login@example.com", remember_me=True)
        ttl = self.redis().ttl(f"refresh:{long.data['refresh']}")
        self.assertAlmostEqual(ttl, 30 * DAY, delta=10)


class RefreshTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="refresh@example.com")
        self.tokens = self.login("refresh@example.com").data

    def refresh(self, token=None, **extra):
        return self.anon().post(aurl("token/refresh"), {"refresh": token or self.tokens["refresh"], **extra}, format="json")

    def test_rotates_the_refresh_token_and_invalidates_the_old_one(self):
        resp = self.refresh()
        self.assertOK(resp)
        self.assertNotEqual(resp.data["refresh"], self.tokens["refresh"])
        self.assertEqual(self.redis().exists(f"refresh:{resp.data['refresh']}"), 1)
        self.assertEqual(self.redis().exists(f"refresh:{self.tokens['refresh']}"), 0)
        self.assertOK(self.refresh(), 401)                 # the old one is dead - replay refused

    def test_the_new_access_token_works(self):
        resp = self.refresh()
        client = self.anon()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        self.assertOK(client.get(aurl("get-user")))

    def test_remember_me_survives_rotation(self):
        long = self.login("refresh@example.com", remember_me=True).data
        rotated = self.refresh(long["refresh"])
        self.assertOK(rotated)
        self.assertAlmostEqual(lifetime_seconds(rotated.data["refresh"]), 30 * DAY, delta=10)
        self.assertTrue(RefreshToken(rotated.data["refresh"])["remember_me"])

    def test_short_sessions_stay_short(self):
        rotated = self.refresh()
        self.assertAlmostEqual(lifetime_seconds(rotated.data["refresh"]), DAY, delta=10)

    def test_missing_unknown_and_expired_refresh_tokens(self):
        self.assertOK(self.anon().post(aurl("token/refresh"), {}, format="json"), 400)
        self.assertOK(self.refresh("not-a-real-token"), 401)
        self.redis().advance(DAY + 1)       # the registry entry expires with the token
        self.assertOK(self.refresh(), 401)

    def test_a_deactivated_or_deleted_account_cannot_keep_refreshing(self):
        self.user.is_deleted, self.user.is_active = True, False
        self.user.save()
        self.assertOK(self.refresh(), 401)

    def test_a_valid_jwt_that_is_not_in_the_registry_is_refused(self):
        stray = str(RefreshToken.for_user(self.user))     # signed, but never registered (e.g. already logged out)
        self.assertOK(self.refresh(stray), 401)


class LogoutTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="logout@example.com")
        self.tokens = self.login("logout@example.com").data

    def authed(self):
        client = self.anon()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")
        return client

    def test_logout_revokes_both_tokens(self):
        resp = self.authed().post(aurl("logout"), {"refresh": self.tokens["refresh"], "access": self.tokens["access"]}, format="json")
        self.assertOK(resp, 205)
        self.assertEqual(self.redis().exists(f"refresh:{self.tokens['refresh']}"), 0)
        self.assertEqual(self.redis().exists(f"access:{self.tokens['access']}"), 0)
        self.assertOK(self.authed().get(aurl("get-user")), 401)                       # session is dead
        self.assertOK(self.anon().post(aurl("token/refresh"), {"refresh": self.tokens["refresh"]}, format="json"), 401)

    def test_logout_without_a_refresh_token_still_succeeds(self):
        self.assertOK(self.authed().post(aurl("logout"), {"access": self.tokens["access"]}, format="json"), 205)

    def test_one_users_refresh_token_cannot_be_used_to_log_another_out(self):
        """REGRESSION: the ownership check was swallowed by a blanket `except Exception`."""
        victim = self.make_user(email="victim@example.com")
        victim_tokens = self.login("victim@example.com").data
        resp = self.authed().post(aurl("logout"), {"refresh": victim_tokens["refresh"]}, format="json")
        self.assertDenied(resp)
        self.assertEqual(self.redis().exists(f"refresh:{victim_tokens['refresh']}"), 1)   # victim still logged in
        self.assertEqual(victim.email, "victim@example.com")

    def test_requires_authentication(self):
        self.assertDenied(self.anon().post(aurl("logout"), {"refresh": self.tokens["refresh"]}, format="json"), 401)


class SessionValidationTests(AccountAPITestCase):
    """ValidatedJWTAuthentication: a signed JWT alone is not enough - it must also be live in Redis."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="session@example.com")
        self.tokens = self.login("session@example.com").data

    def call(self, header):
        client = self.anon()
        if header:
            client.credentials(HTTP_AUTHORIZATION=header)
        return client.get(aurl("get-user"))

    def test_valid_session(self):
        self.assertOK(self.call(f"Bearer {self.tokens['access']}"))

    def test_no_header_garbage_and_wrong_scheme_are_401(self):
        self.assertOK(self.call(None), 401)
        self.assertOK(self.call("Bearer not-a-jwt"), 401)
        self.assertOK(self.call(f"Token {self.tokens['access']}"), 401)

    def test_a_signed_token_missing_from_redis_is_rejected(self):
        self.redis().flushall()
        resp = self.call(f"Bearer {self.tokens['access']}")
        self.assertOK(resp, 401)
        self.assertIn("invalidated", str(resp.data))

    def test_the_session_expires_with_the_access_token_lifetime(self):
        self.redis().advance(30 * 60 + 1)
        self.assertOK(self.call(f"Bearer {self.tokens['access']}"), 401)

    def test_a_refresh_token_cannot_be_used_as_an_access_token(self):
        self.assertOK(self.call(f"Bearer {self.tokens['refresh']}"), 401)

    def test_a_soft_deleted_user_with_a_live_token_is_refused(self):
        self.user.is_deleted, self.user.is_active = True, False
        self.user.save()
        self.assertOK(self.call(f"Bearer {self.tokens['access']}"), 401)

    def test_the_wrong_error_is_not_reported_for_a_bad_password(self):
        """Login failures keep their own message (the exception handler no longer overwrites it)."""
        resp = self.login("session@example.com", password="nope-nope")
        self.assertOK(resp, 401)
        self.assertNotIn("session has been invalidated", str(resp.data))
