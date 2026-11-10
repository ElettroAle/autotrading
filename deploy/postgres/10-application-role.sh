#!/bin/sh
# Runs once, when PostgreSQL initialises its data directory. The application role can log in but owns nothing,
# so the row level security of the owned tables always applies to it (rule tech-sqlalchemy).
set -eu
password="$(cat /run/secrets/postgres_app_password)"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
-- A failing statement must never reach the server log with the password in it.
SET log_min_error_statement TO panic;
CREATE ROLE autotrading_app LOGIN PASSWORD '${password}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO autotrading_app;
GRANT USAGE ON SCHEMA public TO autotrading_app;
SQL
