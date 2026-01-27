# Task App

A Django REST Framework application for task management with organizations, teams, projects, and sprints.

## Tech Stack

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.5.3
- **Python**: 3.12

---

## ⚡ Quick Start (Choose One)

### Option A: Docker Setup (Recommended - Fastest)

#### Prerequisites
- Docker and Docker Compose installed

#### Steps

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

The app will automatically:
- ✅ Create the PostgreSQL database and user
- ✅ Apply all migrations
- ✅ Start the Django development server at `http://localhost:8000`
- ✅ Start Celery worker for async tasks
- ✅ Start Redis for caching and message queue

---

### Option B: Local Setup Without Docker

#### Prerequisites
- Python 3.12+
- PostgreSQL 15 (installed locally)
- Redis 7 (installed locally)
- Git

#### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Task-app
   ```

2. **Create virtual environment**
   
   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   
   **macOS/Linux:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create environment configuration**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with local database settings:
   ```env
   SECRET_KEY=<generate-new-secret-key>
   POSTGRES_DB=task_db
   POSTGRES_USER=task_user
   POSTGRES_PASSWORD=<your-password>
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

5. **Start PostgreSQL and Redis locally**
   
   **macOS (using Homebrew):**
   ```bash
   brew install postgresql redis
   brew services start postgresql
   brew services start redis
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install postgresql redis-server
   sudo systemctl start postgresql
   sudo systemctl start redis-server
   ```
   
   **Windows:**
   - Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)
   - Download and install from [redis.io](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/) or use WSL2

6. **Create the database**
   ```bash
   # Connect to PostgreSQL
   psql -U postgres
   
   # In PostgreSQL shell:
   CREATE DATABASE task_db;
   CREATE USER task_user WITH PASSWORD '<your-password>';
   GRANT ALL PRIVILEGES ON DATABASE task_db TO task_user;
   \q
   ```

7. **Run migrations**
   ```bash
   python manage.py migrate
   ```

8. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser --email admin@example.com
   ```

9. **Start development server**
   ```bash
   python manage.py runserver
   ```

10. **In another terminal, start Celery worker**
    ```bash
    celery -A config.celery worker --loglevel=info
    ```

---

## 🌐 Accessing the Application

### With Docker:
- **Django API**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (user: `task_user`)
- **Redis**: `localhost:6379`

### Without Docker:
- **Django API**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (user: `task_user`)
- **Redis**: `localhost:6379`

---

## 📚 Common Commands

### Docker Commands

```bash
# Start/stop all services
docker compose up -d              # Start in background
docker compose down               # Stop all containers
docker compose down -v            # Stop and remove volumes

# View logs
docker compose logs -f web        # Django logs (live)
docker compose logs -f celery     # Celery logs (live)
docker compose logs -f db         # PostgreSQL logs
docker compose logs -f redis      # Redis logs

# Django management commands
docker compose exec -T web python manage.py <command>

# Examples:
docker compose exec -T web python manage.py makemigrations
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py createsuperuser
docker compose exec -T web python manage.py shell
docker compose exec -T web bash   # Access container shell

# Check service status
docker compose ps                 # List all services
docker compose logs               # View all logs
```

### Local (Non-Docker) Commands

```bash
# Activate virtual environment (if not already activated)
source .venv/bin/activate         # macOS/Linux
.\.venv\Scripts\Activate.ps1      # Windows PowerShell

# Django management
python manage.py runserver        # Start dev server
python manage.py migrate          # Run migrations
python manage.py makemigrations   # Create migrations
python manage.py createsuperuser  # Create admin user
python manage.py shell            # Django shell

# Celery (in separate terminal)
celery -A config.celery worker --loglevel=info

# Stop services
# Press Ctrl+C in the terminal running the server
# Or use systemctl on Linux:
sudo systemctl stop postgresql
sudo systemctl stop redis-server
```

---

## 🏗️ Database Schema

The application includes models for:

- **Accounts**: User authentication and profiles
- **Organizations**: Team/company organization  
- **Teams**: Teams within organizations
- **Projects**: Projects within teams
- **Sprints**: Development sprints
- **Tasks**: Individual tasks with assignments
- **Comments**: Task comments and discussions

---

## ✨ Key Features

- User authentication and authorization
- Organization and team management
- Project and task tracking
- Sprint planning
- Async email notifications via Celery
- Redis caching
- RESTful API with Django REST Framework
- Comprehensive permission system

---

## 📁 Project Structure

```
├── app/                          # Django applications
│   ├── accounts/                # User management & authentication
│   ├── comments/                # Task comments
│   ├── organizations/           # Organization management
│   ├── projects/                # Project management
│   ├── sprints/                 # Sprint management
│   ├── tasks/                   # Task management
│   └── teams/                   # Team management
├── config/                       # Django configuration
│   ├── settings.py              # Main settings
│   ├── urls.py                  # URL routing
│   ├── wsgi.py                  # WSGI config
│   └── celery.py                # Celery configuration
├── core/                         # Core utilities
│   ├── models.py                # Base models
│   ├── permissions/             # Permission classes
│   └── utils.py                 # Utility functions
├── services/                     # Business logic
│   ├── notification_services.py # Notifications
│   ├── token_service.py         # Token management
│   ├── otp_service.py           # OTP handling
│   └── invite_token_service.py  # Invite tokens
├── scripts/                      # Utility scripts
│   ├── wait_for_db.sh           # Docker startup script
│   └── init-db.sql              # PostgreSQL initialization
├── docs/                         # Documentation
│   ├── API_REFERENCE.md         # API documentation
│   ├── DEVELOPER_GUIDE.md       # Development guide
│   └── GIT_WORKFLOW.md          # Git workflow
├── docker-compose.yml            # Docker services
├── Dockerfile                    # Docker image
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── manage.py                     # Django CLI
```

---

## 🔒 Security Notes

### Environment Variables
- **`.env` is git-ignored** - Never commit sensitive data
- **`.env.example`** - Template file (safe to commit)
- Always create `.env` from `.env.example` on new deployments

### Generating SECRET_KEY
```bash
# Python
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Or in Django shell
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
```

### Production Recommendations
- Set `DEBUG=False` in production
- Configure `ALLOWED_HOSTS` properly
- Use environment variables for all secrets
- Set up HTTPS/SSL
- Use a secrets manager (not plain `.env`)
- Use managed database and Redis services
- Set up proper logging and monitoring
- Configure CORS properly for API access

---

## 🐛 Troubleshooting

### Docker Issues

**Containers won't start**
```bash
# Check logs
docker compose logs

# Clean rebuild
docker compose down -v
docker compose up --build
```

**Database connection refused**
- Ensure `POSTGRES_HOST=db` in `.env` (not `localhost`)
- Check PostgreSQL is healthy: `docker compose ps`
- View logs: `docker compose logs db`

**Redis connection refused**
- Verify Redis service is running: `docker compose ps`
- Check logs: `docker compose logs redis`

**Migrations fail**
```bash
# Clear volumes and rebuild
docker compose down -v
docker compose up --build
```

**Port already in use**
- Change ports in `docker-compose.yml`:
  ```yaml
  ports:
    - "8001:8000"    # Use 8001 instead of 8000
  ```

### Local Setup Issues

**Python version mismatch**
```bash
# Check Python version
python --version

# Should be 3.12+. If not, use python3.12:
python3.12 -m venv .venv
```

**PostgreSQL connection refused**
```bash
# Verify PostgreSQL is running
# macOS:
brew services list

# Linux:
sudo systemctl status postgresql

# Windows:
# Check Services application
```

**Redis not running**
```bash
# Start Redis
# macOS:
brew services start redis

# Linux:
sudo systemctl start redis-server
```

**Migrations fail**
```bash
# Reset database
python manage.py migrate zero accounts
python manage.py migrate
```

**Dependencies installation fails**
```bash
# Upgrade pip and try again
python -m pip install --upgrade pip
pip install --upgrade setuptools wheel
pip install -r requirements.txt
```

---

## 📖 Additional Documentation

- [API Reference](docs/API_REFERENCE.md) - Detailed API endpoints
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Development practices
- [Git Workflow](docs/GIT_WORKFLOW.md) - Branching strategy
- [CONTRIBUTING](CONTRIBUTING.md) - Contribution guidelines

---

## 🚀 Deployment

For production deployment guidance, see [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)

Key considerations:
- Use Gunicorn/uWSGI for WSGI server
- Set up Nginx as reverse proxy
- Configure environment-specific settings
- Use managed database services
- Set up monitoring and logging
- Configure backup strategies

---

## 📝 License

[Add your license here]

---

## 👥 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style
- Testing requirements
- Pull request process
- Reporting bugs
- Suggesting features

---

## 📞 Support

For issues and questions:
- Check [Troubleshooting](#troubleshooting) section
- Review [docs/](docs/) directory
- Open an issue on GitHub

---

**Last Updated**: January 2026
**Status**: Active Development
