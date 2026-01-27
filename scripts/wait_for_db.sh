#!/bin/sh

# The environment variables should already be set by docker-compose via env_file
# No need to manually export from .env - docker-compose handles it

echo "Environment check:"
echo "POSTGRES_HOST=${POSTGRES_HOST}"
echo "POSTGRES_USER=${POSTGRES_USER}"
echo "POSTGRES_DB=${POSTGRES_DB}"

echo "Waiting for postgres..."
while ! nc -z db 5432; do
  sleep 1
done

echo "PostgreSQL started!"

# Wait a bit more for PostgreSQL to be fully ready
sleep 2

# Create database if it doesn't exist by connecting to default 'postgres' database
echo "Creating database '$POSTGRES_DB' if it doesn't exist..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB" 2>/dev/null || true

echo "Waiting for redis..."
while ! nc -z redis 6379; do
  sleep 1
done

echo "Redis started!"

# Run migrations and start server
python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
