# Developer Guide

## 🧱 Project Overview
This backend powers a Jira-like task management app built with Django REST Framework, PostgreSQL, and Redis.

## ⚙️ Local Development Setup

### 1. Clone and Setup
```bash
git clone https://github.com/<your-username>/task-app.git
cd task-app
cp .env.example .env
docker-compose up --build
```

### 2. Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### 3. Access
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
docker-compose exec web pytest
```

---

## 🚀 Deployment (Later)
Will use Docker + Gunicorn + Nginx (TBD)

---

## 🔁 Updating This Document
Whenever setup changes (new env var, package, or migration step), update this file.
