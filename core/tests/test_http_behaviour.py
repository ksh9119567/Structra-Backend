"""
Cross-cutting HTTP behaviour: error format, pagination envelope, authentication
required everywhere, and "bad input is a 4xx, never a 500".
"""
from django.test import SimpleTestCase

from core.exceptions import custom_exception_handler
from core.pagination import StandardPagination
from core.testing.base import API, BaseAPITestCase


class ExceptionHandlerTests(BaseAPITestCase):
    def test_unauthenticated_requests_get_a_detail_message(self):
        resp = self.anon().get(f"{API}/accounts/get-user/")
        self.assertOK(resp, 401)
        self.assertIn("detail", resp.data)

    def test_a_bad_password_keeps_its_own_message(self):
        self.make_user(email="a@example.com")
        resp = self.anon().post(f"{API}/accounts/login/", {"email": "a@example.com", "password": "wrong"}, format="json")
        self.assertOK(resp, 401)
        self.assertNotIn("invalidated", str(resp.data))

    def test_validation_errors_are_field_keyed(self):
        resp = self.anon().post(f"{API}/accounts/register/", {}, format="json")
        self.assertOK(resp, 400)
        self.assertIn("email", resp.data)
        self.assertIn("password", resp.data)

    def test_the_handler_defers_to_drf(self):
        self.assertIsNone(custom_exception_handler(RuntimeError("boom"), {}))


class PaginationTests(SimpleTestCase):
    def test_defaults(self):
        pagination = StandardPagination()
        self.assertEqual(pagination.page_size, 20)
        self.assertEqual(pagination.max_page_size, 100)
        self.assertEqual(pagination.page_size_query_param, "page_size")


class EveryEndpointRequiresAuthenticationTests(BaseAPITestCase):
    """A table of every route that is NOT meant to be public: anonymous callers must get 401."""

    PROTECTED = [
        ("get", "accounts/get-user/"), ("put", "accounts/update_user/"), ("delete", "accounts/delete_user/"),
        ("post", "accounts/logout/"),
        ("get", "organizations/get-org/"), ("post", "organizations/create-org/"),
        ("get", "organizations/get-org-details/"), ("get", "organizations/get-org-members/"),
        ("delete", "organizations/self-remove-member/"), ("put", "organizations/update-org/"),
        ("post", "organizations/sent-invite/"), ("post", "organizations/accept-org-invite/"),
        ("put", "organizations/update-member/"), ("put", "organizations/update-owner/"),
        ("delete", "organizations/remove-member/"), ("delete", "organizations/delete-org/"),
        ("get", "teams/get-user-teams/"), ("post", "teams/create-team/"), ("get", "teams/get-org-teams/"),
        ("get", "teams/get-team-details/"), ("get", "teams/get-team-members/"),
        ("delete", "teams/self-remove-member/"), ("put", "teams/update-team/"), ("post", "teams/sent-invite/"),
        ("post", "teams/accept-team-invite/"), ("put", "teams/update-member/"), ("delete", "teams/remove-member/"),
        ("delete", "teams/delete-team/"), ("put", "teams/transfer-owner/"),
        ("get", "projects/get-user-projects/"), ("post", "projects/create-project/"),
        ("get", "projects/get_org-projects/"), ("get", "projects/get-team-projects/"),
        ("get", "projects/get-project-details/"), ("get", "projects/get-project-members/"),
        ("delete", "projects/self-remove-member/"), ("put", "projects/update-project/"),
        ("post", "projects/send-invite/"), ("post", "projects/accept-project-invite/"),
        ("put", "projects/update-member/"), ("delete", "projects/remove-member/"),
        ("put", "projects/transfer-owner/"), ("delete", "projects/delete-project/"),
        ("get", "projects/get-project-teams/"), ("get", "projects/get-stale-members/"),
        ("post", "projects/assign-team/"), ("put", "projects/update-team-role/"), ("delete", "projects/unassign-team/"),
        ("get", "tasks/get-project-tasks/"), ("get", "tasks/get-my-tasks/"), ("post", "tasks/create-task/"),
        ("get", "tasks/get_task_details/"), ("put", "tasks/update-task/"), ("delete", "tasks/delete-task/"),
        ("get", "governance/get-org-settings/"), ("get", "governance/get-team-settings/"),
        ("get", "governance/get-project-settings/"), ("put", "governance/update-org-settings/"),
        ("put", "governance/update-team-settings/"), ("put", "governance/update-project-settings/"),
        ("get", "activity-logs/"), ("get", "activity-logs/stats/"), ("get", "activity-logs/my_activities/"),
    ]

    PUBLIC = [
        ("post", "accounts/register/"), ("post", "accounts/login/"), ("post", "accounts/token/refresh/"),
        ("post", "accounts/get-otp/"), ("post", "accounts/verify-otp/"), ("post", "accounts/verify-otp/login/"),
        ("post", "accounts/forgot-password/request/"), ("post", "accounts/forgot-password/verify/"),
        ("put", "accounts/forgot-password/reset/"),
    ]

    def test_anonymous_callers_are_refused_everywhere_that_matters(self):
        client = self.anon()
        for method, path in self.PROTECTED:
            resp = getattr(client, method)(f"{API}/{path}", {}, format="json")
            self.assertEqual(resp.status_code, 401, f"{method.upper()} {path} answered {resp.status_code}")

    def test_the_public_endpoints_do_not_demand_a_session(self):
        client = self.anon()
        for method, path in self.PUBLIC:
            resp = getattr(client, method)(f"{API}/{path}", {}, format="json")
            self.assertNotEqual(resp.status_code, 401, f"{method.upper()} {path}")
            self.assertLess(resp.status_code, 500, f"{method.upper()} {path} crashed")


class BadInputIsNeverAServerErrorTests(BaseAPITestCase):
    """Garbage ids and empty bodies must produce a 4xx on every endpoint that takes them."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user()
        self.client = self.client_for(self.user)

    GET_WITH_ID = [
        ("organizations/get-org-details/", "org_id"), ("organizations/get-org-members/", "org_id"),
        ("teams/get-team-details/", "team_id"), ("teams/get-team-members/", "team_id"), ("teams/get-org-teams/", "org_id"),
        ("projects/get-project-details/", "project_id"), ("projects/get-project-members/", "project_id"),
        ("projects/get-project-teams/", "project_id"), ("projects/get-stale-members/", "project_id"),
        ("projects/get_org-projects/", "org_id"), ("projects/get-team-projects/", "team_id"),
        ("tasks/get-project-tasks/", "project_id"), ("tasks/get_task_details/", "task_id"),
        ("governance/get-org-settings/", "org_id"), ("governance/get-team-settings/", "team_id"),
        ("governance/get-project-settings/", "project_id"),
    ]

    def test_malformed_ids_on_reads(self):
        for path, param in self.GET_WITH_ID:
            for bad in ("not-a-uuid", "00000000-0000-0000-0000-000000000000", "1", "' OR 1=1 --"):
                resp = self.client.get(f"{API}/{path}?{param}={bad}")
                self.assertTrue(400 <= resp.status_code < 500, f"GET {path}?{param}={bad} -> {resp.status_code}")

    def test_missing_ids_on_reads(self):
        for path, _param in self.GET_WITH_ID:
            resp = self.client.get(f"{API}/{path}")
            self.assertTrue(400 <= resp.status_code < 500, f"GET {path} -> {resp.status_code}")

    def test_empty_bodies_on_writes(self):
        writes = [
            ("post", "organizations/create-org/"), ("post", "teams/create-team/"), ("post", "projects/create-project/"),
            ("post", "tasks/create-task/"), ("put", "organizations/update-org/"), ("put", "teams/update-team/"),
            ("put", "projects/update-project/"), ("put", "tasks/update-task/"), ("delete", "projects/delete-project/"),
            ("delete", "teams/delete-team/"), ("delete", "tasks/delete-task/"), ("post", "projects/send-invite/"),
            ("post", "teams/sent-invite/"), ("post", "organizations/sent-invite/"), ("post", "projects/assign-team/"),
            ("put", "projects/update-team-role/"), ("delete", "projects/unassign-team/"),
            ("put", "projects/transfer-owner/"), ("put", "teams/transfer-owner/"), ("put", "organizations/update-owner/"),
            ("put", "projects/update-member/"), ("put", "teams/update-member/"), ("put", "organizations/update-member/"),
            ("delete", "projects/remove-member/"), ("delete", "teams/remove-member/"), ("delete", "organizations/remove-member/"),
        ]
        for method, path in writes:
            resp = getattr(self.client, method)(f"{API}/{path}", {}, format="json")
            self.assertTrue(400 <= resp.status_code < 500, f"{method.upper()} {path} -> {resp.status_code}")
