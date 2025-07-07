#!/bin/bash
set -e

echo "Starting TimeTrack application (PostgreSQL-only mode)..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h db -p 5432 -U "$POSTGRES_USER" > /dev/null 2>&1; do
    echo "PostgreSQL is not ready yet. Waiting..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Initialize database tables if they don't exist
echo "Ensuring database tables exist..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created/verified')
"

# Run PostgreSQL-only migrations
echo ""
echo "=== Running PostgreSQL Migrations ==="
if [ -f "migrations/run_postgres_migrations.py" ]; then
    echo "Applying PostgreSQL schema updates..."
    python migrations/run_postgres_migrations.py
    if [ $? -ne 0 ]; then
        echo "⚠️  Some migrations failed, but continuing..."
    fi
else
    echo "PostgreSQL migration runner not found, skipping..."
fi

# Start the Flask application with gunicorn
echo ""
echo "=== Starting Application ==="
echo "Starting Flask application with gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app