"""
Activity tracking: the middleware that records every API call, the read-only
activity-log API, and the retention command.
"""
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from core.models import ActivityLog
from core.testing.base import API, BaseAPITestCase

LOGS = f"{API}/activity-logs/"


def make_log(user=None, **fields):
    fields.setdefault("action", "READ")
    fields.setdefault("method", "GET")
    fields.setdefault("path", "/api/v1/x/")
    fields.setdefault("status_code", 200)
    return ActivityLog.objects.create(user=user, username=user.email if user else "Anonymous", **fields)


class MiddlewareTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="tracked@example.com")

    def last(self):
        return ActivityLog.objects.order_by("-timestamp").first()

    def test_an_authenticated_read_is_recorded_with_the_user(self):
        self.client_for(self.user).get(f"{API}/accounts/get-user/")
        log = self.last()
        self.assertEqual((log.user, log.username), (self.user, "tracked@example.com"))
        self.assertEqual((log.action, log.method, log.status_code), ("READ", "GET", 200))
        self.assertEqual(log.path, f"{API}/accounts/get-user/")
        self.assertEqual(log.resource_type, "Account")
        self.assertIsNotNone(log.response_time_ms)

    def test_a_zero_millisecond_request_still_records_its_timing(self):
        """REGRESSION: `if response_time` treated 0.0 ms as 'no timing' and stored NULL."""
        with mock.patch("core.middleware.activity_tracking.time.perf_counter", return_value=100.0):
            self.client_for(self.user).get(f"{API}/accounts/get-user/")
        self.assertEqual(self.last().response_time_ms, 0.0)

    def test_a_create_records_the_resource_name_from_the_response(self):
        self.client_for(self.user).post(f"{API}/projects/create-project/", {"name": "Tracked Project"}, format="json")
        log = self.last()
        self.assertEqual((log.action, log.status_code, log.resource_name), ("CREATE", 201, "Tracked Project"))
        self.assertEqual(log.description, "CREATE Project: Tracked Project")

    def test_updates_and_deletes_map_to_their_actions(self):
        project = self.make_project(self.user)
        client = self.client_for(self.user)
        client.put(f"{API}/projects/update-project/", {"project_id": str(project.id), "name": "N"}, format="json")
        self.assertEqual(self.last().action, "UPDATE")
        client.delete(f"{API}/projects/delete-project/", {"project_id": str(project.id)}, format="json")
        self.assertEqual(self.last().action, "DELETE")

    def test_failed_requests_are_marked_failed(self):
        self.client_for(self.user).get(f"{API}/projects/get-project-details/?project_id=00000000-0000-0000-0000-000000000000")
        log = self.last()
        self.assertEqual((log.action, log.status_code), ("FAILED", 404))

    def test_anonymous_requests_are_recorded_without_a_user(self):
        self.anon().get(f"{API}/accounts/get-user/")
        log = self.last()
        self.assertIsNone(log.user)
        self.assertEqual((log.username, log.status_code, log.action), ("Anonymous", 401, "FAILED"))

    def test_login_and_logout_are_recognised(self):
        self.anon().post(f"{API}/accounts/login/", {"email": "tracked@example.com", "password": self.PASSWORD}, format="json")
        self.assertEqual(self.last().action, "LOGIN")
        client = self.client_for(self.user)
        client.post(f"{API}/accounts/logout/", {}, format="json")
        self.assertEqual(self.last().action, "LOGOUT")

    def test_query_params_and_resource_id_are_captured(self):
        project = self.make_project(self.user)
        self.client_for(self.user).get(f"{API}/projects/get-project-details/?project_id={project.id}")
        log = self.last()
        self.assertEqual(log.resource_id, str(project.id))
        self.assertEqual(log.query_params, {"project_id": [str(project.id)]})

    def test_the_client_ip_prefers_the_first_forwarded_address(self):
        client = self.client_for(self.user)
        client.get(f"{API}/accounts/get-user/", HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1")
        self.assertEqual(self.last().ip_address, "203.0.113.7")
        client.get(f"{API}/accounts/get-user/")
        self.assertEqual(self.last().ip_address, "127.0.0.1")

    def test_the_user_agent_is_truncated(self):
        self.client_for(self.user).get(f"{API}/accounts/get-user/", HTTP_USER_AGENT="x" * 900)
        self.assertEqual(len(self.last().user_agent), 500)

    def test_excluded_paths_and_untracked_methods_are_skipped(self):
        before = ActivityLog.objects.count()
        self.anon().get("/static/app.css")
        self.anon().options(f"{API}/accounts/get-user/")
        self.assertEqual(ActivityLog.objects.count(), before)

    def test_passwords_and_tokens_never_reach_the_log(self):
        secret = "Sup3r-Secret-Pass!"
        self.anon().post(f"{API}/accounts/register/", {"email": "n@example.com", "password": secret}, format="json")
        self.anon().post(f"{API}/accounts/login/", {"email": "n@example.com", "password": secret}, format="json")
        for log in ActivityLog.objects.all():
            blob = " ".join(str(v) for v in (log.request_body, log.query_params, log.extra_data, log.description, log.path))
            self.assertNotIn(secret, blob)

    def test_a_logging_failure_never_breaks_the_response(self):
        with mock.patch("core.middleware.activity_tracking.ActivityLog.objects.create", side_effect=RuntimeError("db down")):
            resp = self.client_for(self.user).get(f"{API}/accounts/get-user/")
        self.assertOK(resp)


class ActivityLogAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.alice, self.bob = self.make_user(), self.make_user()
        self.staff = self.make_user(is_staff=True)
        make_log(self.alice, description="alice-one", action="CREATE", status_code=201, resource_type="Project")
        make_log(self.alice, description="alice-two", action="READ", status_code=200, resource_type="Task")
        make_log(self.alice, description="alice-fail", action="FAILED", status_code=404, resource_type="Project")
        make_log(self.bob, description="bob-one", action="READ", status_code=200, resource_type="Team")

    def descriptions(self, resp):
        rows = resp.data["results"] if "results" in resp.data else resp.data["data"]
        return {r["description"] for r in rows}

    def test_a_user_sees_only_their_own_activity(self):
        resp = self.client_for(self.alice).get(LOGS)
        self.assertOK(resp)
        found = self.descriptions(resp)
        self.assertTrue({"alice-one", "alice-two", "alice-fail"} <= found)
        self.assertNotIn("bob-one", found)

    def test_staff_sees_everyone(self):
        found = self.descriptions(self.client_for(self.staff).get(LOGS))
        self.assertTrue({"alice-one", "bob-one"} <= found)

    def test_retrieve_own_but_not_someone_elses(self):
        own = ActivityLog.objects.get(description="alice-one")
        other = ActivityLog.objects.get(description="bob-one")
        client = self.client_for(self.alice)
        self.assertOK(client.get(f"{LOGS}{own.id}/"))
        self.assertOK(client.get(f"{LOGS}{other.id}/"), 404)
        self.assertOK(self.client_for(self.staff).get(f"{LOGS}{other.id}/"))

    def test_my_activities_is_available_to_regular_users(self):
        """REGRESSION: it fell through to IsAdminUser although it only ever shows the caller's own rows."""
        resp = self.client_for(self.alice).get(f"{LOGS}my_activities/")
        self.assertOK(resp)
        self.assertEqual(resp.data["message"], "Success")
        found = self.descriptions(resp)
        self.assertTrue({"alice-one", "alice-two", "alice-fail"} <= found)
        self.assertNotIn("bob-one", found)
        self.assertEqual(resp.data["count"], len(resp.data["data"]))

    def test_my_activities_is_capped_at_fifty_newest(self):
        for i in range(60):
            make_log(self.bob, description=f"bulk-{i}")
        resp = self.client_for(self.bob).get(f"{LOGS}my_activities/")
        self.assertEqual(resp.data["count"], 50)

    def test_stats_is_available_to_regular_users_and_scoped_to_them(self):
        """REGRESSION: same fall-through to IsAdminUser."""
        before = ActivityLog.objects.filter(user=self.alice).count()
        resp = self.client_for(self.alice).get(f"{LOGS}stats/")
        self.assertOK(resp)
        data = resp.data["data"]
        self.assertEqual(data["total_activities"], before)
        self.assertEqual(data["by_action"]["CREATE"], 1)
        self.assertEqual(data["by_action"]["FAILED"], 1)
        self.assertEqual(data["by_resource"]["Project"], 2)
        self.assertEqual(data["by_status"]["success_2xx"], 2)
        self.assertEqual(data["by_status"]["client_error_4xx"], 1)
        self.assertEqual(data["by_status"]["server_error_5xx"], 0)

    def test_stats_for_staff_cover_everyone(self):
        before = ActivityLog.objects.count()
        resp = self.client_for(self.staff).get(f"{LOGS}stats/")
        self.assertEqual(resp.data["data"]["total_activities"], before)

    def test_filters(self):
        client = self.client_for(self.alice)
        self.assertEqual(self.descriptions(client.get(f"{LOGS}?action=CREATE")), {"alice-one"})
        self.assertEqual(self.descriptions(client.get(f"{LOGS}?status_code=404")), {"alice-fail"})
        self.assertEqual(self.descriptions(client.get(f"{LOGS}?resource_type=project")), {"alice-one", "alice-fail"})
        self.assertEqual(self.descriptions(client.get(f"{LOGS}?status_code_gte=400&status_code_lte=499")), {"alice-fail"})

    def test_search_and_ordering(self):
        client = self.client_for(self.alice)
        self.assertEqual(self.descriptions(client.get(f"{LOGS}?search=alice-two")), {"alice-two"})
        resp = client.get(f"{LOGS}?ordering=status_code&action=READ&search=alice")
        self.assertOK(resp)

    def test_staff_can_filter_by_username(self):
        found = self.descriptions(self.client_for(self.staff).get(f"{LOGS}?username={self.bob.email}"))
        self.assertIn("bob-one", found)
        self.assertNotIn("alice-one", found)

    def test_pagination(self):
        resp = self.client_for(self.alice).get(f"{LOGS}?page_size=2")
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])

    def test_requires_authentication(self):
        for path in (LOGS, f"{LOGS}my_activities/", f"{LOGS}stats/"):
            self.assertDenied(self.anon().get(path), 401)

    def test_the_log_is_read_only(self):
        for user in (self.alice, self.staff):
            client = self.client_for(user)
            self.assertIn(client.post(LOGS, {"action": "READ"}, format="json").status_code, (403, 405))
            self.assertIn(client.delete(f"{LOGS}{ActivityLog.objects.first().id}/").status_code, (403, 405))
        self.assertOK(self.client_for(self.staff).post(LOGS, {"action": "READ"}, format="json"), 405)


class CleanupCommandTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        user = self.make_user()
        self.old = make_log(user, description="old")
        self.recent = make_log(user, description="recent")
        ActivityLog.objects.filter(pk=self.old.pk).update(timestamp=timezone.now() - timedelta(days=120))

    def run_command(self, *args):
        out = StringIO()
        call_command("cleanup_activity_logs", *args, stdout=out)
        return out.getvalue()

    def test_deletes_logs_older_than_the_default_ninety_days(self):
        output = self.run_command()
        self.assertIn("Successfully deleted", output)
        self.assertFalse(ActivityLog.objects.filter(pk=self.old.pk).exists())
        self.assertTrue(ActivityLog.objects.filter(pk=self.recent.pk).exists())

    def test_days_option(self):
        ActivityLog.objects.filter(pk=self.recent.pk).update(timestamp=timezone.now() - timedelta(days=10))
        self.run_command("--days", "5")
        self.assertEqual(ActivityLog.objects.count(), 0)

    def test_dry_run_deletes_nothing(self):
        output = self.run_command("--dry-run")
        self.assertIn("DRY RUN", output)
        self.assertEqual(ActivityLog.objects.count(), 2)

    def test_nothing_to_clean(self):
        ActivityLog.objects.filter(pk=self.old.pk).delete()
        self.assertIn("No old activity logs found", self.run_command())
        self.assertEqual(ActivityLog.objects.count(), 1)
