# Developer Guide

## 🧱 Project Overview
Structra-Backed is a Jira-like task management backend built with Django REST Framework, PostgreSQL, and Redis.

## 📋 Recent Updates (February 2026)

### Model Changes
- **Soft Delete Implementation**: Added `is_deleted` field to User, Organization, Team, Project, and Task models
- **Role Field Constraints**: Updated TeamMembership and ProjectMembership to use `null=False, blank=False` for role fields (consistent with OrganizationMembership)
- **Task Model Improvements**:
  - Added `on_delete=models.CASCADE` to `created_by` ForeignKey
  - Added `limit_choices_to={"parent__isnull": True}` to parent field to prevent circular parent-child relationships
  - Removed redundant `null=True` and `max_length` from description field

### API Changes
- All list endpoints now filter out deleted entities using `is_deleted=False`
- Utility functions updated to exclude deleted entities from queries
- Serializer validation queries updated to check only non-deleted entities

### Database
- New migrations created for all model changes
- All migrations applied successfully

## ⚙️ Local Development Setup

### 1. Clone and Setup
```bash
git clone https://github.com/ksh9119567/Structra-Backend.git
cd Structra-Backend
cp .env.example .env
docker-compose up --build
```

### 2. Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### 3. Run Migrations
```bash
docker-compose exec web python manage.py migrate
```

### 4. Access
- API: http://127.0.0.1:8000/api/v1/
- Admin: http://127.0.0.1:8000/admin

---

## 💡 Branching Workflow
Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for branch naming and PR rules.

Typical flow:
```bash
git checkout develop
git checkout -b feature/<your-feature>
```

---

## 🧩 Directory Structure
```
accounts/    # user, auth
projects/    # projects, teams, org
tasks/       # tasks, sprints, comments
docs/        # internal documentation
```

---

## 🧪 Testing
```bash
python manage.py test                 # whole suite - no Postgres / Redis / Docker needed
scripts/run_tests.sh teams projects   # per app (Windows: .\scripts\run_tests.ps1 teams projects)
docker-compose exec web python manage.py test
```

Every app has a `tests/` package (`app/<app>/tests/`, shared helpers in `core/testing/`,
cross-cutting tests in `core/tests/`). See [TESTING.md](TESTING.md) for per-app commands,
what is covered, and how to write new tests.

---

## 🔐 Soft Delete Implementation

All core entities support soft delete:
- Users are marked as deleted but remain in database
- Organizations, Teams, Projects, and Tasks follow the same pattern
- Deleted entities are automatically filtered from all API responses
- Use `is_deleted=False` filter in queries to exclude deleted entities

Example:
```python
# Automatically excludes deleted users
from core.utils.base_utils import get_user
user = get_user('email@example.com')  # Returns None if user is deleted

# Direct query
from app.accounts.models import User
active_users = User.objects.filter(is_deleted=False)
```

---

## 🚀 Deployment (Later)
Will use Docker + Gunicorn + Nginx (TBD)

---

## 🔁 Updating This Document
Whenever setup changes (new env var, package, or migration step), update this file.
