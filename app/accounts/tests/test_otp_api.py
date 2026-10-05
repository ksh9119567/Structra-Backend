"""
One-time passwords: request (get-otp), verify (verify-otp) and passwordless login
(verify-otp/login).
"""
from django.core import mail

from .helpers import AccountAPITestCase, aurl


class GetOTPTests(AccountAPITestCase):
    def request(self, **overrides):
        data = {"kind": "email", "identifier": "otp@example.com", "purpose": "login", **overrides}
        return self.anon().post(aurl("get-otp"), data, format="json")

    def test_email_otp_is_stored_and_mailed(self):
        self.assertOK(self.request())
        otp = self.otp("login", "email", "otp@example.com")
        self.assertRegex(otp, r"^\d{6}$")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["otp@example.com"])
        self.assertIn(otp, mail.outbox[0].body)

    def test_phone_otp_is_stored_without_sending_mail(self):
        self.assertOK(self.request(kind="phone", identifier="+15551234567"))
        self.assertRegex(self.otp("login", "phone", "+15551234567"), r"^\d{6}$")
        self.assertEqual(len(mail.outbox), 0)

    def test_the_otp_expires_after_five_minutes(self):
        self.request()
        self.assertAlmostEqual(self.redis().ttl("otp:login:email:otp@example.com"), 300, delta=3)
        self.redis().advance(301)
        self.assertIsNone(self.otp("login", "email", "otp@example.com"))

    def test_requesting_again_replaces_the_previous_code(self):
        self.request()
        first = self.otp("login", "email", "otp@example.com")
        for _ in range(20):                      # 1-in-a-million collision; retry makes it impossible in practice
            self.request()
            if self.otp("login", "email", "otp@example.com") != first:
                break
        self.assertEqual(self.redis().keys("otp:login:email:otp@example.com"), ["otp:login:email:otp@example.com"])

    def test_purposes_are_kept_apart(self):
        self.request(purpose="login")
        self.request(purpose="verify")
        self.assertIsNotNone(self.otp("login", "email", "otp@example.com"))
        self.assertIsNotNone(self.otp("verify", "email", "otp@example.com"))

    def test_validation(self):
        self.assertOK(self.request(kind="fax"), 400)
        self.assertOK(self.request(purpose="hack"), 400)
        self.assertOK(self.request(identifier=""), 400)
        self.assertOK(self.anon().post(aurl("get-otp"), {"kind": "email"}, format="json"), 400)

    def test_otps_are_not_all_the_same(self):
        seen = set()
        for i in range(8):
            self.request(identifier=f"u{i}@example.com")
            seen.add(self.otp("login", "email", f"u{i}@example.com"))
        self.assertGreater(len(seen), 1)


class VerifyOTPTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="verify@example.com", verified=False, phone_no="+15551234567")

    def request_otp(self, kind="email", identifier="verify@example.com"):
        self.anon().post(aurl("get-otp"), {"kind": kind, "identifier": identifier, "purpose": "verify"}, format="json")
        return self.otp("verify", kind, identifier)

    def verify(self, otp, kind="email", identifier="verify@example.com"):
        return self.anon().post(aurl("verify-otp"), {"kind": kind, "identifier": identifier, "otp": otp}, format="json")

    def test_correct_code_verifies_the_email(self):
        otp = self.request_otp()
        self.assertOK(self.verify(otp))
        self.assertTrue(self.fresh(self.user).is_email_verified)

    def test_correct_code_verifies_the_phone(self):
        otp = self.request_otp("phone", "+15551234567")
        self.assertOK(self.verify(otp, "phone", "+15551234567"))
        user = self.fresh(self.user)
        self.assertTrue(user.is_phone_verified)
        self.assertFalse(user.is_email_verified)

    def test_wrong_code_is_rejected_and_changes_nothing(self):
        otp = self.request_otp()
        wrong = "000000" if otp != "000000" else "111111"
        self.assertOK(self.verify(wrong), 400)
        self.assertFalse(self.fresh(self.user).is_email_verified)

    def test_a_code_is_single_use(self):
        otp = self.request_otp()
        self.assertOK(self.verify(otp))
        self.assertOK(self.verify(otp), 400)

    def test_an_expired_code_is_rejected(self):
        otp = self.request_otp()
        self.redis().advance(301)
        self.assertOK(self.verify(otp), 400)

    def test_no_code_was_ever_requested(self):
        self.assertOK(self.verify("123456"), 400)

    def test_brute_force_is_throttled_even_for_the_right_code(self):
        otp = self.request_otp()
        wrong = "000000" if otp != "000000" else "111111"
        for _ in range(5):
            self.assertOK(self.verify(wrong), 400)
        resp = self.verify(otp)                       # 6th attempt in the window
        self.assertOK(resp, 400)
        self.assertIn("Too many", str(resp.data))
        self.assertFalse(self.fresh(self.user).is_email_verified)

    def test_the_attempt_window_resets_after_five_minutes(self):
        wrong = "000000"
        self.request_otp()
        for _ in range(6):
            self.verify(wrong)
        self.redis().advance(301)
        otp = self.request_otp()
        self.assertOK(self.verify(otp))

    def test_a_login_code_cannot_be_used_to_verify(self):
        self.anon().post(aurl("get-otp"), {"kind": "email", "identifier": "verify@example.com", "purpose": "login"}, format="json")
        login_code = self.otp("login", "email", "verify@example.com")
        self.assertOK(self.verify(login_code), 400)

    def test_unknown_user_after_a_valid_code_is_400(self):
        otp = self.request_otp(identifier="ghost@example.com")
        self.assertOK(self.verify(otp, identifier="ghost@example.com"), 400)

    def test_validation(self):
        self.assertOK(self.anon().post(aurl("verify-otp"), {"kind": "email", "identifier": "x@example.com"}, format="json"), 400)
        self.assertOK(self.anon().post(aurl("verify-otp"), {"kind": "fax", "identifier": "x", "otp": "1"}, format="json"), 400)


class OTPLoginTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="otplogin@example.com", phone_no="+15557654321")

    def code(self, kind="email", identifier="otplogin@example.com"):
        self.anon().post(aurl("get-otp"), {"kind": kind, "identifier": identifier, "purpose": "login"}, format="json")
        return self.otp("login", kind, identifier)

    def login_with(self, otp, kind="email", identifier="otplogin@example.com"):
        return self.anon().post(aurl("verify-otp/login"), {"kind": kind, "identifier": identifier, "otp": otp}, format="json")

    def test_email_otp_logs_the_user_in_with_working_tokens(self):
        resp = self.login_with(self.code())
        self.assertOK(resp)
        self.assertEqual(resp.data["user"]["email"], "otplogin@example.com")
        client = self.anon()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        self.assertOK(client.get(aurl("get-user")))

    def test_phone_otp_logs_the_user_in(self):
        resp = self.login_with(self.code("phone", "+15557654321"), "phone", "+15557654321")
        self.assertOK(resp)
        self.assertEqual(resp.data["user"]["email"], "otplogin@example.com")

    def test_the_email_match_is_case_insensitive(self):
        otp = self.code(identifier="OtpLogin@Example.com")
        self.assertOK(self.login_with(otp, identifier="OtpLogin@Example.com"))

    def test_wrong_and_replayed_codes_are_rejected(self):
        otp = self.code()
        self.assertOK(self.login_with("000000" if otp != "000000" else "111111"), 400)
        self.assertOK(self.login_with(otp))
        self.assertOK(self.login_with(otp), 400)

    def test_a_verify_code_cannot_be_used_to_log_in(self):
        self.anon().post(aurl("get-otp"), {"kind": "email", "identifier": "otplogin@example.com", "purpose": "verify"}, format="json")
        verify_code = self.otp("verify", "email", "otplogin@example.com")
        self.assertOK(self.login_with(verify_code), 400)

    def test_brute_force_is_throttled(self):
        otp = self.code()
        wrong = "000000" if otp != "000000" else "111111"
        for _ in range(5):
            self.login_with(wrong)
        self.assertOK(self.login_with(otp), 400)

    def test_an_unregistered_address_gets_a_clean_400_not_a_500(self):
        """REGRESSION: get_user() returned None and login_user(None) crashed."""
        otp = self.code(identifier="ghost@example.com")
        self.assertOK(self.login_with(otp, identifier="ghost@example.com"), 400)

    def test_a_deactivated_account_cannot_get_tokens(self):
        self.user.is_active = False
        self.user.save()
        self.assertOK(self.login_with(self.code()), 400)

    def test_a_soft_deleted_account_cannot_get_tokens(self):
        self.user.is_deleted, self.user.is_active = True, False
        self.user.save()
        self.assertOK(self.login_with(self.code()), 400)
