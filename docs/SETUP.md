# Setup & Installation Guide

This guide explains how to run the Task App using Docker (recommended) or on your local machine without Docker.

## Prerequisites

### For Docker Setup
- Git
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose

### For Local Setup
- Git
- Python 3.12+
- PostgreSQL 15
- Redis 7

---

## Option A: Docker Setup (Recommended & Fastest)

Docker automatically handles all service setup and configuration.

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd Task-app
```

### Step 2: Create Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` and update these values for security:
```env
SECRET_KEY=<generate-new-secret-key>
POSTGRES_PASSWORD=<strong-password>
EMAIL_HOST_PASSWORD=<your-email-password>
```

**Generate SECRET_KEY:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Step 3: Start Services

```bash
docker compose up -d
```

The system will automatically:
- ✅ Create PostgreSQL database and user
- ✅ Apply all migrations
- ✅ Start Django development server
- ✅ Start Celery worker
- ✅ Start Redis

### Step 4: Verify Setup

```bash
docker compose ps
```

All services should show "Up" status.

### Accessing the Application

- **API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Database**: localhost:5432 (user: `task_user`)
- **Redis**: localhost:6379

### Create Superuser (Optional)

```bash
docker compose exec -T web python manage.py createsuperuser --email admin@example.com
```

### Common Docker Commands

```bash
# View logs
docker compose logs -f web          # Django logs
docker compose logs -f celery       # Celery logs
docker compose logs -f db           # PostgreSQL logs
docker compose logs -f redis        # Redis logs

# Run management commands
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py makemigrations
docker compose exec -T web python manage.py createsuperuser
docker compose exec -T web python manage.py shell
docker compose exec -T web bash     # Access container shell

# Service management
docker compose down                 # Stop all services
docker compose down -v              # Stop and remove volumes
docker compose restart              # Restart services
docker compose ps                   # Check service status
```

---

## Option B: Local Setup Without Docker

### Prerequisites Installation

#### macOS (using Homebrew)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL and Redis
brew install postgresql redis

# Start services
brew services start postgresql
brew services start redis

# Verify services
brew services list
```

#### Linux (Ubuntu/Debian)

```bash
# Update package manager
sudo apt-get update

# Install PostgreSQL and Redis
sudo apt-get install -y postgresql postgresql-contrib redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Verify services
sudo systemctl status postgresql
sudo systemctl status redis-server

# Enable services to start on boot
sudo systemctl enable postgresql
sudo systemctl enable redis-server
```

#### Windows

**Option 1: Using WSL2 (Recommended)**
- Install WSL2 and Ubuntu
- Follow the Linux instructions above

**Option 2: Direct Installation**
- Download PostgreSQL from https://www.postgresql.org/download/windows/
- Download Redis from https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/
- Follow their installation wizards

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd Task-app
```

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\\venv\\Scripts\\Activate.ps1
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Environment Configuration

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
REDIS_DB=0
REDIS_PASSWORD=
```

### Step 5: Create Database

**macOS/Linux:**
```bash
# Connect to PostgreSQL as default user
sudo -u postgres psql
```

**Windows:**
```bash
# Connect using pgAdmin or psql
psql -U postgres
```

In the PostgreSQL shell:
```sql
CREATE DATABASE task_db;
CREATE USER task_user WITH PASSWORD '<your-password>';
GRANT ALL PRIVILEGES ON DATABASE task_db TO task_user;
ALTER DATABASE task_db OWNER TO task_user;
\\q
```

### Step 6: Run Migrations

```bash
python manage.py migrate
```

### Step 7: Create Superuser (Optional)

```bash
python manage.py createsuperuser --email admin@example.com
```

### Step 8: Start Development Server

In one terminal:
```bash
python manage.py runserver
```

In another terminal (with virtual environment activated):
```bash
celery -A config.celery worker --loglevel=info
```

### Accessing the Application

- **API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Database**: localhost:5432
- **Redis**: localhost:6379

### Common Local Commands

```bash
# Activate virtual environment (if not already activated)
source .venv/bin/activate              # macOS/Linux
.\\venv\\Scripts\\Activate.ps1            # Windows PowerShell

# Django management
python manage.py runserver             # Start dev server
python manage.py migrate               # Run migrations
python manage.py makemigrations        # Create migrations
python manage.py createsuperuser       # Create admin user
python manage.py shell                 # Django shell
python manage.py check                 # Check for issues

# Celery (in separate terminal)
celery -A config.celery worker --loglevel=info

# Deactivate virtual environment
deactivate

# Stop services (Linux)
sudo systemctl stop postgresql
sudo systemctl stop redis-server

# Stop services (macOS)
brew services stop postgresql
brew services stop redis
```

---

## Troubleshooting

### Docker Issues

**Containers won't start**
```bash
# Check all logs
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
- Try: `docker compose restart redis`

**Migrations fail**
```bash
# Clear volumes and rebuild
docker compose down -v
docker compose up --build
```

**Port already in use**
- Change ports in `docker-compose.yml`:
  ```yaml
  web:
    ports:
      - "8001:8000"    # Use 8001 instead of 8000
  db:
    ports:
      - "5433:5432"    # Use 5433 instead of 5432
  ```

**Permissions error in Linux**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
sudo systemctl restart docker

# Log out and log back in for changes to take effect
```

### Local Setup Issues

**Python version mismatch**
```bash
# Check Python version
python --version

# Should be 3.12 or higher
# If not, use python3.12 or python3.13:
python3.12 -m venv .venv
```

**PostgreSQL connection refused**
```bash
# Check if PostgreSQL is running
# macOS:
brew services list

# Linux:
sudo systemctl status postgresql

# Start PostgreSQL
# macOS:
brew services start postgresql

# Linux:
sudo systemctl start postgresql
```

**PostgreSQL password authentication failed**
```bash
# Reset password for postgres user (Linux)
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'newpassword';
\\q
```

**Redis not running**
```bash
# Start Redis
# macOS:
brew services start redis

# Linux:
sudo systemctl start redis-server

# Verify
redis-cli ping
# Should return: PONG
```

**Dependencies installation fails**
```bash
# Upgrade pip and tools
python -m pip install --upgrade pip setuptools wheel

# Install with verbose output
pip install -v -r requirements.txt

# Check for conflicting packages
pip check
```

**Migrations fail**
```bash
# Reset migrations (careful - this deletes data!)
python manage.py migrate zero
python manage.py migrate

# Or reset specific app
python manage.py migrate zero accounts
python manage.py migrate accounts
```

**Virtual environment not activating**
- Ensure you're in the project root directory
- Try deleting and recreating: `rm -rf .venv && python3 -m venv .venv`
- Verify activation: `which python` should show `.venv/bin/python`

**ModuleNotFoundError after pip install**
```bash
# Reinstall requirements
pip install --force-reinstall -r requirements.txt

# Clear pip cache
pip cache purge
```

**Port 5432 already in use**
```bash
# Find process using port (macOS/Linux)
lsof -i :5432

# Kill process
kill -9 <PID>

# Or change PostgreSQL port in .env
POSTGRES_PORT=5433
```

---

## Environment Variables Reference

### Required Variables

```env
# Django
SECRET_KEY=<your-secret-key>
DEBUG=False  # Set to False in production

# Database
POSTGRES_DB=task_db
POSTGRES_USER=task_user
POSTGRES_PASSWORD=<your-password>
POSTGRES_HOST=db          # Use 'db' for Docker, 'localhost' for local
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis          # Use 'redis' for Docker, 'localhost' for local
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=           # Leave empty if not configured

# Celery
CELERY_BROKER_URL=redis://redis:6379/1      # Update host for local setup
CELERY_RESULT_BACKEND=redis://redis:6379/2  # Update host for local setup

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<your-email@gmail.com>
EMAIL_HOST_PASSWORD=<your-app-password>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=TaskApp <no-reply@taskapp.local>
```

---

## Next Steps

After setup:
1. Create a superuser if not done: `python manage.py createsuperuser`
2. Check [API_REFERENCE.md](API_REFERENCE.md) for API endpoints
3. Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for development practices
4. Review [GIT_WORKFLOW.md](GIT_WORKFLOW.md) if contributing

---

**Last Updated**: January 2026
