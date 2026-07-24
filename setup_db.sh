#!/usr/bin/env bash
# Phase 0 DB setup. Run manually — installs MySQL, creates DB/user, imports Chinook.
# Review each step before running; edit DB_USER/DB_PASSWORD before executing.
set -euo pipefail

DB_NAME="chinook"
DB_USER="chinook_app"
DB_PASSWORD="devraj1109"   # match MYSQL_PASSWORD in your .env
SQL_FILE="$(dirname "$0")/data/Chinook_MySql.sql"

echo "==> 1. Install MySQL (Homebrew)"
if ! command -v mysql >/dev/null 2>&1; then
    brew install mysql
    brew services start mysql
else
    echo "mysql already on PATH, skipping install"
fi

echo "==> 2. Create database + app user (run as root/admin MySQL user)"
mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME};
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "==> 3. Import Chinook schema + data"
mysql -u root "${DB_NAME}" < "${SQL_FILE}"

echo "==> 4. Verify"
mysql -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SELECT COUNT(*) AS track_count FROM Track;"

echo "Done. Copy .env.example to .env and fill in matching values."
