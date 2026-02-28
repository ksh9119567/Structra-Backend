-- Create database and user if they don't exist
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'structra_db') THEN
      CREATE DATABASE structra_db;
   END IF;
END
$do$;

-- Create user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'structra_user') THEN
      CREATE USER structra_user WITH PASSWORD 'structra1234';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE structra_db TO structra_user;
ALTER DATABASE structra_db OWNER TO structra_user;
