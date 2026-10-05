# Changelog

All notable changes will be documented in this file.

---

## [Unreleased]
### Added
- Automated test-suite for every app (`app/<app>/tests/`, `core/tests/`) with in-memory
  SQLite / fake Redis / eager Celery - run with `python manage.py test`
  or `scripts/run_tests.sh <app>` (see `docs/TESTING.md`)
- `config/settings_test.py`, `core/testing/` (fake Redis + `BaseAPITestCase` factories)
- `GET get-user-projects/` now also lists projects reached through an assigned team
- Governance backstop (org / owning-team owner) can now delete projects and administer
  project members; an org owner can delete a team, transfer its ownership and administer its members

### Fixed
- **Team member removal froze the request**: a leftover `ipdb.set_trace()` in `remove_team_member`
- Missing / deleted / malformed ids returned HTTP 500 instead of 404 (`get_org`, `get_team`,
  `get_project`, `get_task`, `get_project_membership`)
- Project / team detail and member listings returned 500 for non-members and for team-derived
  participants; org members could not view a team they are not in (now 403 / 200 as designed)
- Accepting an invite as the wrong user, or as someone already a member, returned 500
  (now 403 / 400); a wrong user no longer burns the invitee's token
- Creating a project / team in an organization you do not belong to crashed (now 404)
- Team: `self_remove` last-manager check crashed (`team.membership`); updating / removing a
  non-member crashed; org owner could not transfer a team
- Subtask creation was refused to almost everyone (inverted permission logic); subtasks can no
  longer be nested
- Account deletion guards compared against lower-case roles, so owners / last admins could
  delete their accounts
- Logout accepted another user's refresh token and revoked their session
- OTP login crashed for unknown addresses and issued tokens to deactivated accounts
- Refresh tokens kept working for deactivated / deleted accounts
- Duplicate emails differing only by case and duplicate phone numbers were accepted,
  which broke OTP / reset lookups (500)
- `my_activities` and `stats` activity-log endpoints were admin-only despite being per-user
- Team / organization member lists ignored the `role` filter, search and ordering
- A soft-deleted team kept granting its members project access; deleted projects / teams
  still counted against organization quotas (and quotas used `==` instead of `>=`)
- Organization VIEWERs could not leave an organization
- Task lists paginated an unordered queryset (rows could repeat / vanish between pages)
- Project create / team create are now atomic (no ownerless half-created rows)
- Activity log stored no response time for very fast requests (0 ms was treated as missing)

### Security
- Invites can no longer grant `OWNER`, or a role at / above the inviter's own (privilege escalation)
- Attaching a team to a project via `update-project` now needs the same authority as `assign-team`
- OTPs are generated with `secrets` instead of `random`
- Organization settings can no longer be re-pointed at another organization

---

## [v0.4.0] - 2026-07-11
### Added
- Governance app: per-entity settings (Organization / Team / Project) auto-created via signals
- Configurable min/max role policies, membership rules, creation controls, limits & default roles
- Rules-resolution engine with settings inheritance (Project ← Team ← Org)
- Activity tracking middleware: automatic audit log of all API requests
- Activity Logs API: list, detail, `my_activities`, and `stats`
- Sensitive-field redaction in logs + activity-log cleanup management command
- Tasks: `get-my-tasks/` cross-project view endpoint

### Changed
- Corrected task/priority choice formats and role choice formats

### Notes
- Approval **workflow** engine is not yet implemented — governance exposes
  `require_approval_for_*` flags, but there is no request/approve/reject queue yet.
- `sprints` and `comments` apps are scaffolded but not yet implemented.

---

## [v0.3.0] - 2026
### Added
- CRUD Projects: org/team-linked or standalone, lifecycle status
  (Planning / Active / On Hold / Completed / Archived)
- Project membership: invite, accept, update role, remove, self-remove, transfer ownership
- CRUD Tasks: status, priority, type, dates, assignee
- Subtask support (self-referential, one level deep)
- Task filtering, search, ordering & pagination

---

## [v0.2.0] - 2026
### Added
- Full Teams module: CRUD, membership invite, roles, ownership transfer
- OTP verification & OTP login
- Forgot-password flow (request → verify → reset)
- Asynchronous email delivery via Celery (OTP & invites)

---

## [v0.1.0] - 2025-11-24
### Added
- Custom User model (email-based)
- JWT authentication (access/refresh in Redis)
- Docker setup (Postgres + Redis + Celery)
- Git workflow and branching rules
- RBAC Skeleton & Permission Classes
- CRUD Organizations, membership invite, roles
- CRUD Teams, membership invite, roles

---

## Upcoming
### Planned
- Approval workflow engine (activate governance approval flags)
- Comments module (task & project discussions, attachments)
- Sprints module (planning, backlog, burndown)
- Notifications (assignments, mentions, invites, due dates)
