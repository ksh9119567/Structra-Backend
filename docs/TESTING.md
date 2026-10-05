# 🧪 Testing Guide

The backend ships with an automated test-suite that exercises every API endpoint,
the permission model and the edge cases around them. It needs **no Postgres, no
Redis, no Celery worker and no Docker** - it is safe to run anywhere, any time.

```bash
python manage.py test            # everything (~5 seconds)
```

`manage.py test` automatically uses `config/settings_test.py`, which swaps every
external dependency for an in-process one:

| Real service | In tests |
|---|---|
| PostgreSQL | in-memory SQLite (or Postgres, see below) |
| Redis (OTPs, token registry, invite/reset tokens, rate limits) | `core/testing/fake_redis.py` - an in-memory double with **expiry and a fast-forward clock** |
| Celery worker | tasks run eagerly, in-process |
| SMTP | captured in `django.core.mail.outbox` |

Your real Redis / database are never read, written or flushed by a test run.

---

## ▶️ Running tests

### Per app (use the helper scripts)

```bash
# Linux / macOS / Git Bash
scripts/run_tests.sh                       # whole suite
scripts/run_tests.sh teams                 # one app
scripts/run_tests.sh teams projects tasks  # several apps
scripts/run_tests.sh projects -v 2         # extra flags go to `manage.py test`
```

```powershell
# Windows PowerShell
.\scripts\run_tests.ps1
.\scripts\run_tests.ps1 teams
.\scripts\run_tests.ps1 teams projects tasks
.\scripts\run_tests.ps1 projects -v 2
```

Apps: `accounts` `organizations` `teams` `projects` `tasks` `governance` `comments` `sprints`
and `core` (shared permissions, utils, activity logging, cross-cutting HTTP behaviour).

### Plain `manage.py` (finer control)

```bash
python manage.py test app.projects                                   # one app
python manage.py test app.projects.tests.test_project_crud_api       # one file
python manage.py test app.projects.tests.test_project_crud_api.ProjectDeleteTests            # one class
python manage.py test app.projects.tests.test_project_crud_api.ProjectDeleteTests.test_org_owner_backstop_can_delete_a_project_they_are_not_in
python manage.py test --failfast            # stop at the first failure
python manage.py test --parallel 4          # faster on big runs
python manage.py test -v 2                  # list every test as it runs
python manage.py test -k backstop           # only tests whose name matches
```

### In Docker

```bash
docker-compose exec web python manage.py test
```

### Against PostgreSQL (optional)

SQLite is used by default because it is instant and dependency-free. To run the
same suite on PostgreSQL (e.g. before a release, to exercise the real partial
unique index and row locking):

```bash
TEST_DB=postgres POSTGRES_HOST=localhost python manage.py test         # bash
$env:TEST_DB="postgres"; $env:POSTGRES_HOST="localhost"; python manage.py test   # PowerShell
```

Django creates and drops a separate `test_<POSTGRES_DB>` database - your real data
is untouched - but the database user needs the `CREATEDB` privilege
(`ALTER USER structra_user CREATEDB;`).

---

## 🗂️ What is covered

Every app has its own `tests/` package. File names say what they cover.

| App | Files | Covers |
|---|---|---|
| **accounts** | `test_models`, `test_auth_api`, `test_profile_api`, `test_otp_api`, `test_password_reset_api`, `test_services` | user manager; register / login / remember-me / token refresh + rotation / logout; the JWT-plus-Redis session check; profile update; account deletion guards; OTP request / verify / OTP login incl. brute-force throttling and expiry; forgot-password flow; OTP, token and invite-token services |
| **organizations** | `test_models`, `test_org_api`, `test_org_members_api` | create / list / retrieve / update / delete / transfer ownership; members, invites, accept-invite, update / remove / self-remove, role-escalation guard |
| **teams** | `test_models`, `test_team_crud_api`, `test_team_members_api` | same matrix for teams, plus org-owner (governance backstop) overrides and what deleting a team revokes |
| **projects** | `test_models`, `test_resolver`, `test_project_crud_api`, `test_project_members_api`, `test_project_teams_api` | project CRUD and quotas; the access resolver (`effective_role`, governance backstop, permission root, explicit-member counting, stale members); members / invites; multi-team assign / update / unassign and team-derived access |
| **tasks** | `test_models`, `test_task_api` | create (+ subtasks), list / filter / search / order / paginate, my-tasks, retrieve, update (assignment rules), delete, per-role permission matrix |
| **governance** | `test_rules_engine`, `test_settings_api` | settings auto-creation, threshold clamping, rule inheritance, settings endpoints and their validation |
| **core** | `test_constants`, `test_permission_classes`, `test_lookup_utils`, `test_activity_logging`, `test_http_behaviour`, `test_testing_tools` | role-ladder integrity; a role-by-role matrix for every DRF permission class; lookup helpers; activity middleware / API / cleanup command; "every protected endpoint refuses anonymous callers"; "bad ids never cause a 500" |
| **comments**, **sprints** | `test_placeholder` | these apps have no models / routes yet - the tests fail the day that changes, as a reminder to add real ones |

### Permission testing approach

* Each API test file builds a project / team / org with **one user per role**
  (owner, manager, lead, contributor, viewer, outsider) and asserts what each can
  and cannot do, including the governance switches (`allow_member_invites`, the
  `*_min_role` thresholds, ...).
* Requests are made with **real JWTs registered in the (fake) Redis session
  registry**, so they go through `ValidatedJWTAuthentication` exactly like production.
* Tests named `test_…` whose docstring starts with **`REGRESSION:`** pin a bug
  that was fixed - if one of them fails, a fixed bug has come back.

---

## ✍️ Writing new tests

Subclass `core.testing.base.BaseAPITestCase`:

```python
from core.testing.base import BaseAPITestCase, API

class MyFeatureTests(BaseAPITestCase):
    def test_manager_can_do_it(self):
        owner, manager, outsider = self.make_user(), self.make_user(), self.make_user()
        project = self.make_project(owner)                       # owner is OWNER automatically
        self.add_project_member(project, manager, "MANAGER")
        self.set_settings(project, allow_member_invites=True)    # tweak governance

        resp = self.client_for(manager).post(f"{API}/projects/send-invite/?project_id={project.id}",
                                             {"email": self.make_user().email}, format="json")
        self.assertOK(resp)                                      # == status 200 with a helpful message
        self.assertDenied(self.client_for(outsider).post(...))   # == status 403
        self.assertDenied(self.anon().post(...), 401)
```

Helpers: `make_user`, `make_org`, `make_team`, `make_project` (optionally with `org=`
and `team=`), `add_org_member` / `add_team_member` / `add_project_member`,
`set_settings`, `client_for(user)`, `anon()`, `redis()`.

Handy tricks:

* **Expiry without sleeping** - `self.redis().advance(301)` fast-forwards the fake clock
  (OTPs live 300 s, access tokens 30 min, invite tokens 24 h, reset tokens 15 min).
* **Read an OTP** - `self.redis().get("otp:login:email:user@example.com")`, or look at
  `django.core.mail.outbox`.
* **Deterministic ordering** - two rows created in the same clock tick can share a
  `created_at` on Windows; pin it with `Model.objects.filter(...).update(created_at=...)`.

### Conventions

* Prefer API-level tests for behaviour and permissions, unit tests for pure logic.
* One behaviour per test; name the test after the rule it protects.
* When you fix a bug, add a test whose docstring starts with `REGRESSION:`.
* Don't `import ipdb` / leave `set_trace()` in application code (one slipped into
  `remove_team_member` once and froze every team-member removal).

---

## 🛠️ Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TypeError: _path_normpath ... NoneType` when running `manage.py test app.x` | `app/__init__.py` is missing (it makes `app` a regular package). It is committed now. |
| `permission denied to create database` | `TEST_DB=postgres` but the DB user lacks `CREATEDB` (see above). |
| `ModuleNotFoundError` for a package | activate the virtualenv: `.task_venv\Scripts\activate` (Windows) / `source .task_venv/bin/activate`. |
| Tests behave differently from the running server | the server uses `config.settings`; tests use `config.settings_test`. Export `DJANGO_SETTINGS_MODULE` to override. |
