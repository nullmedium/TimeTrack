#!/bin/bash
set -e

echo "Starting TimeTrack application (PostgreSQL-only mode)..."

# Check for debug/bypass mode
if [ "$SKIP_MIGRATIONS" = "true" ]; then
    echo "⚠️  SKIP_MIGRATIONS=true - Skipping all migration steps!"
else
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
            
            # Don't exit in debug mode
            if [ "$DEBUG_MODE" = "true" ]; then
                echo "⚠️  DEBUG_MODE=true - Continuing despite migration failure..."
                echo "⚠️  The application may not work correctly!"
                echo ""
                echo "To debug, you can:"
                echo "  1. docker exec -it <container> bash"
                echo "  2. python diagnose_migrations.py"
                echo "  3. flask db current"
                echo ""
            else
                echo "To bypass migrations for debugging, restart with:"
                echo "  SKIP_MIGRATIONS=true docker-compose up"
                echo "Or:"
                echo "  DEBUG_MODE=true docker-compose up"
                exit 1
            fi
        else
            echo "✅ Database migrations completed successfully"
        fi
    else
        echo "⚠️  No migrations directory found. Initializing Flask-Migrate..."
        
        # Try to initialize, but don't exit if it fails
        python docker_migrate_init.py
        if [ $? -ne 0 ]; then
            echo "❌ Migration initialization failed!"
            
            if [ "$DEBUG_MODE" = "true" ]; then
                echo "⚠️  DEBUG_MODE=true - Continuing without migrations..."
                echo "⚠️  The database may not be properly initialized!"
            else
                echo "To debug the issue:"
                echo "  1. Set DEBUG_MODE=true and restart"
                echo "  2. docker exec -it <container> bash"
                echo "  3. python docker_migrate_init.py"
                exit 1
            fi
        else
            # Check if database has existing tables
            python -c "
from app import app, db
with app.app_context():
    inspector = db.inspect(db.engine)
    tables = [t for t in inspector.get_table_names() if t != 'alembic_version']
    if tables:
        print('has_tables')
" > /tmp/db_check.txt 2>/dev/null || echo "db_check_failed" > /tmp/db_check.txt
            
            if grep -q "has_tables" /tmp/db_check.txt 2>/dev/null; then
                echo "📊 Existing database detected. Marking as current..."
                flask db stamp head
                echo "✅ Database marked as current"
            elif grep -q "db_check_failed" /tmp/db_check.txt 2>/dev/null; then
                echo "⚠️  Could not check database tables"
                if [ "$DEBUG_MODE" != "true" ]; then
                    exit 1
                fi
            else
                echo "🆕 Empty database detected. Creating tables..."
                flask db upgrade
                if [ $? -ne 0 ]; then
                    echo "❌ Failed to create database tables!"
                    if [ "$DEBUG_MODE" != "true" ]; then
                        exit 1
                    fi
                else
                    echo "✅ Database tables created"
                fi
            fi
            
            rm -f /tmp/db_check.txt
        fi
    fi

    # Legacy migration support (can be removed after full transition)
    if [ -f "migrations_old/run_postgres_migrations.py" ]; then
        echo ""
        echo "=== Checking Legacy Migrations ==="
        echo "Found old migration system. Consider removing after confirming Flask-Migrate is working."
    fi
fi

# Start the Flask application with gunicorn
echo ""
echo "=== Starting Application ==="
echo "Starting Flask application with gunicorn..."

# In debug mode, start with more verbose logging
if [ "$DEBUG_MODE" = "true" ]; then
    echo "🐛 Running in DEBUG MODE with verbose logging"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 2 --timeout 30 --log-level debug --access-logfile - --error-logfile - app:app
else
    exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app
fi