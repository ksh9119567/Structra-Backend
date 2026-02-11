-- Create database and user if they don't exist
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'task_db') THEN
      CREATE DATABASE task_db;
   END IF;
END
$do$;

-- Create user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'task_user') THEN
      CREATE USER task_user WITH PASSWORD 'task1234';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE task_db TO task_user;
ALTER DATABASE task_db OWNER TO task_user;
