from django.conf import settings
from django.test import SimpleTestCase

from core.testing.base import BaseAPITestCase
from core.testing.fake_redis import FakeRedis


class FakeRedisTests(SimpleTestCase):
    """The test double must behave like the Redis commands the project relies on."""

    def setUp(self):
        self.r = FakeRedis()

    def test_setex_get_roundtrip_returns_str(self):
        self.r.setex("k", 60, 123)
        self.assertEqual(self.r.get("k"), "123")

    def test_missing_key(self):
        self.assertIsNone(self.r.get("nope"))
        self.assertEqual(self.r.exists("nope"), 0)

    def test_keys_expire_when_clock_advances(self):
        self.r.setex("otp", 300, "111111")
        self.assertEqual(self.r.exists("otp"), 1)
        self.r.advance(299)
        self.assertEqual(self.r.exists("otp"), 1)
        self.r.advance(2)
        self.assertEqual(self.r.exists("otp"), 0)
        self.assertIsNone(self.r.get("otp"))

    def test_incr_starts_at_one_and_keeps_expiry(self):
        self.assertEqual(self.r.incr("c"), 1)
        self.r.expire("c", 60)
        self.assertEqual(self.r.incr("c"), 2)
        self.assertGreater(self.r.ttl("c"), 0)
        self.r.advance(61)
        self.assertEqual(self.r.incr("c"), 1)  # window elapsed -> counter restarts

    def test_delete_returns_number_removed(self):
        self.r.setex("a", 60, "1")
        self.assertEqual(self.r.delete("a", "missing"), 1)
        self.assertEqual(self.r.exists("a"), 0)

    def test_ttl_codes(self):
        self.assertEqual(self.r.ttl("missing"), -2)
        self.r.set("plain", "x")
        self.assertEqual(self.r.ttl("plain"), -1)

    def test_keys_pattern(self):
        self.r.setex("otp:email:a", 60, "1")
        self.r.setex("otp:phone:b", 60, "2")
        self.r.setex("other", 60, "3")
        self.assertCountEqual(self.r.keys("otp:*"), ["otp:email:a", "otp:phone:b"])


class TestSettingsWiringTests(BaseAPITestCase):
    """Guards that the suite really runs isolated from real services."""

    def test_redis_client_is_the_fake(self):
        self.assertIsInstance(settings.REDIS_CLIENT, FakeRedis)

    def test_database_is_not_the_dev_database(self):
        # Under the default test settings the DB is SQLite in memory.
        # (TEST_DB=postgres runs against Django's separate test_<name> database.)
        name = str(settings.DATABASES["default"]["NAME"])
        self.assertNotEqual(name, "structra_db")

    def test_email_goes_to_the_in_memory_outbox(self):
        self.assertIn("locmem", settings.EMAIL_BACKEND)

    def test_redis_is_reset_between_tests_part_one(self):
        self.redis().setex("leak-check", 60, "1")
        self.assertEqual(self.redis().exists("leak-check"), 1)

    def test_redis_is_reset_between_tests_part_two(self):
        # runs in its own test - the key from the sibling test must be gone
        self.assertEqual(self.redis().exists("leak-check"), 0)

    def test_client_for_authenticates_through_real_jwt(self):
        user = self.make_user()
        resp = self.client_for(user).get("/api/v1/accounts/get-user/")
        self.assertOK(resp)
        self.assertEqual(resp.data["data"]["email"], user.email)

    def test_anonymous_is_rejected(self):
        self.assertDenied(self.anon().get("/api/v1/accounts/get-user/"), 401)
