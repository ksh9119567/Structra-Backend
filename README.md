# Task App

A Django REST Framework application for task management with organizations, teams, projects, and sprints.

## Tech Stack

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.5.3
- **Python**: 3.12

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed

### Setup & Run

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Task-app
   ```

2. **Create environment configuration**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and update the following for security:
   - `SECRET_KEY` - Generate a new Django secret key
   - `POSTGRES_PASSWORD` - Set a strong PostgreSQL password
   - `EMAIL_HOST_PASSWORD` - Set your email provider credentials

3. **Build and run containers**
   ```bash
   docker compose up -d
   ```

4. **Verify all services are running**
   ```bash
   docker compose ps
   ```

The app will:
- Automatically create the PostgreSQL database and user
- Apply all migrations
- Start the Django development server at `http://localhost:8000`
- Start Celery worker for async tasks
- Start Redis for caching and message queue

### Accessing the Application

- **Django API**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (user: `task_user`, password: as set in `.env`)
- **Redis**: `localhost:6379`

## Common Commands

```bash
# View logs
docker compose logs -f web          # Django logs
docker compose logs -f celery       # Celery logs
docker compose logs -f db           # PostgreSQL logs
docker compose logs -f redis        # Redis logs

# Run Django management commands
docker compose exec -T web python manage.py <command>

# Make migrations
docker compose exec -T web python manage.py makemigrations

# Stop all containers
docker compose down

# Remove all containers and volumes
docker compose down -v
```

## Database Schema

The application includes models for:
- **Accounts**: User authentication and profiles
- **Organizations**: Team/company organization
- **Teams**: Teams within organizations
- **Projects**: Projects within teams
- **Sprints**: Development sprints
- **Tasks**: Individual tasks with assignments

## Key Features

- User authentication and authorization
- Organization and team management
- Project and task tracking
- Sprint planning
- Async email notifications via Celery
- Redis caching

## Project Structure

```
├── app/                    # Django applications
│   ├── accounts/          # User management
│   ├── organizations/     # Organization management
│   ├── teams/             # Team management
│   ├── projects/          # Project management
│   ├── sprints/           # Sprint management
│   └── tasks/             # Task management
├── config/                # Django configuration
├── core/                  # Core utilities and permissions
├── services/              # Business logic services
├── scripts/               # Utility scripts
│   └── init-db.sql       # PostgreSQL initialization
└── docs/                  # Documentation
```

## Development Notes

- Migrations are applied automatically on container startup via `scripts/wait_for_db.sh`
- The PostgreSQL database and user are created automatically via `scripts/init-db.sql`
- All configuration is managed via environment variables in `.env`
- The `.env` file is gitignored for security - use `.env.example` as a template

## Troubleshooting

If containers fail to start:

1. Check logs: `docker compose logs`
2. Ensure ports 8000, 5432, 6379 are available
3. Try rebuilding: `docker compose down -v && docker compose up --build`

For database issues:
- Verify `POSTGRES_PASSWORD` in `.env` matches docker-compose setup
- Check PostgreSQL logs: `docker compose logs db`

For Celery issues:
- Verify Redis is running: `docker compose logs redis`
- Check Celery logs: `docker compose logs celery`
