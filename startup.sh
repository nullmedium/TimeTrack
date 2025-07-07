#!/bin/bash
set -e

echo "Starting TimeTrack application..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h db -p 5432 -U "$POSTGRES_USER" > /dev/null 2>&1; do
    echo "PostgreSQL is not ready yet. Waiting..."
    sleep 2
done
echo "PostgreSQL is ready!"

# SQLite to PostgreSQL migration is now handled by the migration system below

# Initialize database tables if they don't exist
echo "Ensuring database tables exist..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created/verified')
"

# Run all database schema migrations
echo ""
echo "=== Running Database Schema Migrations ==="
if [ -d "migrations" ] && [ -f "migrations/run_all_db_migrations.py" ]; then
    echo "Checking and applying database schema updates..."
    python migrations/run_all_db_migrations.py
    if [ $? -ne 0 ]; then
        echo "⚠️  Some database migrations had issues, but continuing..."
    fi
else
    echo "No migrations directory found, skipping database migrations..."
fi

# Run code migrations to update code for model changes
echo ""
echo "=== Running Code Migrations ==="
echo "Code migrations temporarily disabled for debugging"
# if [ -d "migrations" ] && [ -f "migrations/run_code_migrations.py" ]; then
#     echo "Checking and applying code updates for model changes..."
#     python migrations/run_code_migrations.py
#     if [ $? -ne 0 ]; then
#         echo "⚠️  Code migrations had issues, but continuing..."
#     fi
# else
#     echo "No migrations directory found, skipping code migrations..."
# fi

# Start the Flask application with gunicorn
echo ""
echo "=== Starting Application ==="
echo "Starting Flask application with gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app