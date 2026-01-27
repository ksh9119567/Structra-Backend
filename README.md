# Task App

A Django REST Framework application for task management with organizations, teams, projects, and sprints.

## Tech Stack

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7  
- **Task Queue**: Celery 5.5.3
- **Python**: 3.12

## Features

- ✨ User authentication and authorization
- 🏢 Organization and team management
- 📋 Project and task tracking
- 🎯 Sprint planning
- 📧 Async email notifications via Celery
- ⚡ Redis caching
- 🔐 Comprehensive permission system
- 📡 RESTful API with Django REST Framework

## Quick Start

### Option A: Docker (Recommended)
```bash
git clone <repository-url>
cd Task-app
cp .env.example .env
docker compose up -d
```

### Option B: Local Setup
See [docs/SETUP.md](docs/SETUP.md) for detailed installation instructions.

## Documentation

- 📖 **[Setup Guide](docs/SETUP.md)** - Complete installation for Docker and local setup
- 🔌 **[API Reference](docs/API_REFERENCE.md)** - API endpoints and usage
- 👨‍💻 **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Development practices
- 🌳 **[Git Workflow](docs/GIT_WORKFLOW.md)** - Branching and contribution process
- 🤝 **[Contributing](CONTRIBUTING.md)** - How to contribute

## Project Structure

```
├── app/                 # Django applications
│   ├── accounts/       # User management
│   ├── organizations/  # Organization management
│   ├── teams/          # Team management
│   ├── projects/       # Project management
│   ├── sprints/        # Sprint management
│   ├── tasks/          # Task management
│   └── comments/       # Task comments
├── config/              # Django configuration
├── core/                # Core utilities & permissions
├── services/            # Business logic services
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── docker-compose.yml   # Docker services
├── requirements.txt     # Python dependencies
└── manage.py            # Django CLI
```

## Access Points

- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Common Commands

```bash
# Docker
docker compose up -d              # Start services
docker compose down               # Stop services
docker compose logs -f web        # View Django logs

# Django
python manage.py migrate          # Run migrations
python manage.py createsuperuser  # Create admin user
python manage.py runserver        # Start dev server
```

**For full command reference, see [docs/SETUP.md](docs/SETUP.md)**

## Environment Configuration

1. Create `.env` from `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Update these variables:
   - `SECRET_KEY` - Generate a new Django secret key
   - `POSTGRES_PASSWORD` - Strong password for PostgreSQL
   - `EMAIL_HOST_PASSWORD` - Email provider credentials

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Troubleshooting

For troubleshooting and common issues, see [docs/SETUP.md#troubleshooting](docs/SETUP.md#troubleshooting).

## License

[Add your license here]

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Status**: Active Development | **Last Updated**: January 2026
