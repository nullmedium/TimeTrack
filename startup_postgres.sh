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

# Run Flask-Migrate migrations
echo ""
echo "=== Running Database Migrations ==="
export FLASK_APP=app.py

# Check if migrations directory exists
if [ -d "migrations" ]; then
    echo "Applying database migrations..."
    flask db upgrade
    if [ $? -ne 0 ]; then
        echo "❌ Migration failed! Check the logs above."
        exit 1
    fi
    echo "✅ Database migrations completed successfully"
else
    echo "⚠️  No migrations directory found. Initializing Flask-Migrate..."
    echo "Using baseline from commit 4214e88..."
    python establish_baseline_4214e88.py
    if [ $? -ne 0 ]; then
        echo "❌ Migration initialization failed!"
        echo "Please run manually: python establish_baseline_4214e88.py"
        exit 1
    fi
    # Stamp the database as being at baseline
    flask db stamp head
    echo "✅ Database marked at baseline commit 4214e88"
fi

# Legacy migration support (can be removed after full transition)
if [ -f "migrations_old/run_postgres_migrations.py" ]; then
    echo ""
    echo "=== Checking Legacy Migrations ==="
    echo "Found old migration system. Consider removing after confirming Flask-Migrate is working."
fi

# Start the Flask application with gunicorn
echo ""
echo "=== Starting Application ==="
echo "Starting Flask application with gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app