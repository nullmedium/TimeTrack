#!/bin/bash
# Manual migration script for TimeTrack SQLite to PostgreSQL
set -e

echo "TimeTrack Database Migration Script"
echo "==================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL not set in .env file"
    exit 1
fi

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "Error: PostgreSQL connection variables not set in .env file"
    exit 1
fi

# Default SQLite path
SQLITE_PATH="${SQLITE_PATH:-/data/timetrack.db}"

echo "Configuration:"
echo "  SQLite DB: $SQLITE_PATH"
echo "  PostgreSQL: $DATABASE_URL"
echo ""

# Check if SQLite database exists
if [ ! -f "$SQLITE_PATH" ]; then
    echo "Error: SQLite database not found at $SQLITE_PATH"
    echo "Please ensure the database file exists or update SQLITE_PATH in .env"
    exit 1
fi

# Check if PostgreSQL is accessible
echo "Testing PostgreSQL connection..."
if ! docker-compose exec postgres pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
    echo "Error: Cannot connect to PostgreSQL. Please ensure docker-compose is running:"
    echo "  docker-compose up -d postgres"
    exit 1
fi

echo "PostgreSQL is accessible!"

# Confirm migration
echo ""
echo "This will:"
echo "1. Create a backup of your SQLite database"
echo "2. Migrate all data from SQLite to PostgreSQL"
echo "3. Verify the migration was successful"
echo ""
read -p "Do you want to proceed? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

# Run migration
echo "Starting migration..."
docker-compose exec timetrack python migrate_sqlite_to_postgres.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Migration completed successfully!"
    echo "Check migration.log for detailed information."
    echo ""
    echo "Your SQLite database has been backed up and the original renamed to .migrated"
    echo "You can now use PostgreSQL as your primary database."
else
    echo ""
    echo "Migration failed! Check migration.log for details."
    echo "Your original SQLite database remains unchanged."
    exit 1
fi