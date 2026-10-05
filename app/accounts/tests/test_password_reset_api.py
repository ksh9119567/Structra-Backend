"""
Forgot-password flow: request OTP -> verify OTP (get reset token) -> reset password.
"""
from django.core import mail

from app.accounts.models import User
from .helpers import AccountAPITestCase, aurl


class PasswordResetTestBase(AccountAPITestCase):
    NEW_PASSWORD = "Brand-New-Pass#2026"

    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="reset@example.com", verified=True)

    def request(self, kind="email", identifier="reset@example.com"):
        return self.anon().post(aurl("forgot-password/request"), {"kind": kind, "identifier": identifier}, format="json")

    def verify(self, otp, kind="email", identifier="reset@example.com"):
        return self.anon().post(aurl("forgot-password/verify"), {"kind": kind, "identifier": identifier, "otp": otp}, format="json")

    def reset(self, token, password=None):
        return self.anon().put(aurl("forgot-password/reset"), {"reset_token": token, "new_password": password or self.NEW_PASSWORD},
                               format="json")

    def reset_otp(self, kind="email", identifier="reset@example.com"):
        return self.otp("password", kind, identifier)

    def token(self, kind="email", identifier="reset@example.com"):
        """Run request + verify and return the reset token."""
        self.request(kind, identifier)
        return self.verify(self.reset_otp(kind, identifier), kind, identifier).data["message"]


class ForgotPasswordRequestTests(PasswordResetTestBase):
    def test_a_verified_user_gets_a_code_by_email(self):
        self.assertOK(self.request())
        self.assertRegex(self.reset_otp(), r"^\d{6}$")
        self.assertEqual([m.to for m in mail.outbox], [["reset@example.com"]])
        self.assertIn(self.reset_otp(), mail.outbox[0].body)

    def test_the_email_match_is_case_insensitive(self):
        self.assertOK(self.request(identifier="RESET@example.com"))

    def test_unknown_user_is_400(self):
        self.assertOK(self.request(identifier="ghost@example.com"), 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_an_unverified_email_must_be_verified_first(self):
        self.make_user(email="unverified@example.com", verified=False)
        resp = self.request(identifier="unverified@example.com")
        self.assertOK(resp, 400)
        self.assertIn("not verified", str(resp.data))

    def test_an_unverified_phone_must_be_verified_first(self):
        self.make_user(email="p@example.com", phone_no="+15550001111")
        self.assertOK(self.request("phone", "+15550001111"), 400)

    def test_a_soft_deleted_account_cannot_reset(self):
        self.user.is_deleted, self.user.is_active = True, False
        self.user.save()
        self.assertOK(self.request(), 400)

    def test_requests_are_rate_limited_per_minute(self):
        for _ in range(5):
            self.assertOK(self.request())
        resp = self.request()
        self.assertOK(resp, 400)
        self.assertIn("Too many", str(resp.data))
        self.redis().advance(61)
        self.assertOK(self.request())

    def test_phone_flow_with_duplicate_numbers_does_not_crash(self):
        """REGRESSION: .get(phone_no=...) raised MultipleObjectsReturned (HTTP 500) on duplicate numbers."""
        for email in ("dup1@example.com", "dup2@example.com"):
            u = User.objects.create_user(email=email, password=self.PASSWORD, phone_no="+15559990000")
            u.is_phone_verified = True
            u.save()
        self.assertOK(self.request("phone", "+15559990000"))

    def test_validation(self):
        self.assertOK(self.anon().post(aurl("forgot-password/request"), {"kind": "email"}, format="json"), 400)
        self.assertOK(self.request("fax", "x"), 400)


class ForgotPasswordVerifyTests(PasswordResetTestBase):
    def test_correct_code_returns_a_reset_token(self):
        self.request()
        resp = self.verify(self.reset_otp())
        self.assertOK(resp)
        self.assertEqual(self.redis().get(f"password_reset_token:{resp.data['message']}"), str(self.user.id))

    def test_wrong_code_is_rejected(self):
        self.request()
        otp = self.reset_otp()
        self.assertOK(self.verify("000000" if otp != "000000" else "111111"), 400)

    def test_a_code_is_single_use(self):
        self.request()
        otp = self.reset_otp()
        self.assertOK(self.verify(otp))
        self.assertOK(self.verify(otp), 400)

    def test_an_expired_code_is_rejected(self):
        self.request()
        otp = self.reset_otp()
        self.redis().advance(301)
        self.assertOK(self.verify(otp), 400)

    def test_brute_force_is_throttled(self):
        self.request()
        otp = self.reset_otp()
        wrong = "000000" if otp != "000000" else "111111"
        for _ in range(5):
            self.assertOK(self.verify(wrong), 400)
        resp = self.verify(otp)
        self.assertOK(resp, 400)
        self.assertIn("Too many", str(resp.data))

    def test_a_code_for_one_address_does_not_work_for_another(self):
        other = self.make_user(email="other@example.com", verified=True)
        self.request()
        otp = self.reset_otp()
        self.assertOK(self.verify(otp, identifier=other.email), 400)


class ForgotPasswordResetTests(PasswordResetTestBase):
    def test_full_flow_changes_the_password(self):
        token = self.token()
        self.assertOK(self.reset(token))
        self.assertOK(self.login("reset@example.com", password=self.NEW_PASSWORD))
        self.assertOK(self.login("reset@example.com", password=self.PASSWORD), 401)

    def test_phone_flow(self):
        user = self.make_user(email="phoneflow@example.com", phone_no="+15553334444")
        user.is_phone_verified = True
        user.save()
        token = self.token("phone", "+15553334444")
        self.assertOK(self.reset(token))
        self.assertOK(self.login("phoneflow@example.com", password=self.NEW_PASSWORD))

    def test_the_token_is_single_use(self):
        token = self.token()
        self.assertOK(self.reset(token))
        self.assertOK(self.reset(token, password="Another-Pass#2027"), 400)
        self.assertOK(self.login("reset@example.com", password=self.NEW_PASSWORD))

    def test_the_token_expires_after_fifteen_minutes(self):
        token = self.token()
        self.redis().advance(15 * 60 + 1)
        self.assertOK(self.reset(token), 400)

    def test_unknown_token_is_rejected(self):
        self.assertOK(self.reset("deadbeef"), 400)

    def test_weak_passwords_are_rejected_and_the_token_survives(self):
        token = self.token()
        for weak in ("short", "password", "12345678901", "aaaaaaaaaa"):
            self.assertOK(self.reset(token, password=weak), 400)
        self.assertOK(self.reset(token))      # still valid after the failed attempts
        self.assertOK(self.login("reset@example.com", password=self.NEW_PASSWORD))

    def test_missing_fields(self):
        self.assertOK(self.anon().put(aurl("forgot-password/reset"), {"reset_token": "x"}, format="json"), 400)
        self.assertOK(self.anon().put(aurl("forgot-password/reset"), {"new_password": "x"}, format="json"), 400)
