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
    
    # Use Docker-friendly initialization (no Git required)
    python docker_migrate_init.py
    if [ $? -ne 0 ]; then
        echo "❌ Migration initialization failed!"
        exit 1
    fi
    
    # Check if database has existing tables
    python -c "
from app import app, db
with app.app_context():
    inspector = db.inspect(db.engine)
    tables = [t for t in inspector.get_table_names() if t != 'alembic_version']
    if tables:
        print('has_tables')
" > /tmp/db_check.txt
    
    if grep -q "has_tables" /tmp/db_check.txt 2>/dev/null; then
        echo "📊 Existing database detected. Marking as current..."
        flask db stamp head
        echo "✅ Database marked as current"
    else
        echo "🆕 Empty database detected. Creating tables..."
        flask db upgrade
        echo "✅ Database tables created"
    fi
    
    rm -f /tmp/db_check.txt
fi

# Legacy migration support (can be removed after full transition)
if [ -f "migrations_old/run_all_db_migrations.py" ]; then
    echo ""
    echo "=== Checking Legacy Migrations ==="
    echo "Found old migration system. Consider removing after confirming Flask-Migrate is working."
fi

# Start the Flask application with gunicorn
echo ""
echo "=== Starting Application ==="
echo "Starting Flask application with gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app