Setup & Installation Guide (Windows, Linux, macOS)
===================================================

This guide explains how to run the Django Task App backend locally using Docker, and how to develop without Docker if needed.

Prerequisites
-------------
- Git
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose
- (Optional) Python 3.12+ and virtualenv for non-Docker dev

Option A: Run with Docker (Recommended)
---------------------------------------
1) Clone the repository:
   - `git clone <your-repo-url>`
   - `cd <repo>`

2) Create `.env` in the project root:
   ```
   SECRET_KEY=your-dev-secret-key
   POSTGRES_DB=task_db
   POSTGRES_USER=task_user
   POSTGRES_PASSWORD=task1234
   POSTGRES_HOST=db
   POSTGRES_PORT=5432

   REDIS_HOST=redis
   REDIS_PORT=6379
   REDIS_DB=0
   REDIS_PASSWORD=
   ```

3) Start the stack:
   - `docker-compose up --build`

4) Access the app:
   - Django: http://127.0.0.1:8000/
   - Admin:  http://127.0.0.1:8000/admin

5) Common container commands:
   - Migrations: `docker-compose exec web python manage.py migrate`
   - Superuser:  `docker-compose exec web python manage.py createsuperuser --email admin@example.com`
   - Shell:      `docker-compose exec web bash`
   - Stop:       `docker-compose down`
   - Stop + volumes: `docker-compose down -v`

6) Logs:
   - `docker-compose logs -f web`
   - `docker-compose logs -f db`
   - `docker-compose logs -f redis`

Option B: Run without Docker (Local Python)
------------------------------------------
1) Create a virtualenv and activate it:
   - Windows (PowerShell): `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`

2) Install dependencies:
   - `python -m pip install --upgrade pip`
   - `pip install -r requirements.txt`

3) Start Postgres and Redis locally:
   - Postgres on 5432, Redis on 6379 (update `.env` accordingly)

4) Create `.env`:
   ```
   SECRET_KEY=your-dev-secret-key
   POSTGRES_DB=task_db
   POSTGRES_USER=task_user
   POSTGRES_PASSWORD=task1234
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432

   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0
   REDIS_PASSWORD=
   ```

5) Run migrations & server:
   - `python manage.py migrate`
   - `python manage.py runserver`

6) Create a superuser:
   - `python manage.py createsuperuser --email admin@example.com`

Windows Notes
-------------
- Use Docker Desktop with WSL2 backend for best performance.
- If ports 5432 or 6379 are in use, adjust `docker-compose.yml` or stop conflicting services.

macOS Notes
-----------
- Install Docker Desktop for macOS.
- Use `brew` for Postgres/Redis if running locally: `brew install postgresql redis`.

Linux Notes
-----------
- Install Docker Engine and docker-compose.
- Ensure your user is in the `docker` group (or use `sudo`).

Troubleshooting
---------------
- DB connection refused:
  - Ensure `POSTGRES_HOST` matches the service name (`db`) when using Docker.
  - Check health: `docker-compose ps` and logs.
- Redis not reachable:
  - Confirm `REDIS_HOST` is `redis` in Docker and port mapped.
- Migrations fail:
  - Clear volumes and rebuild: `docker-compose down -v && docker-compose up --build`.
- 500 errors:
  - Check application logs: `docker-compose logs -f web`.

Production Hints (Later)
------------------------
- Use Gunicorn behind a reverse proxy (Nginx).
- Set `DEBUG=False`, configure `ALLOWED_HOSTS`.
- Use a managed Postgres/Redis service.
- Serve media on S3/minio with presigned URLs.
- Use a secrets manager instead of plain `.env`.
