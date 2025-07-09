#!/bin/bash
# Debug entrypoint for troubleshooting migration issues

echo "=== TimeTrack Debug Entrypoint ==="
echo ""
echo "This entrypoint keeps the container running for debugging."
echo "The application is NOT started automatically."
echo ""

# Set Flask app
export FLASK_APP=app.py

# Wait for PostgreSQL if needed
if [ -n "$DATABASE_URL" ] || [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h ${POSTGRES_HOST:-db} -p ${POSTGRES_PORT:-5432} -U "$POSTGRES_USER" > /dev/null 2>&1; do
        echo "PostgreSQL is not ready yet. Waiting..."
        sleep 2
    done
    echo "✅ PostgreSQL is ready!"
fi

echo ""
echo "=== Environment Info ==="
echo "FLASK_APP: $FLASK_APP"
echo "DATABASE_URL: ${DATABASE_URL:-(not set)}"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo ""

echo "=== Quick Diagnostics ==="

# Check if migrations directory exists
if [ -d "migrations" ]; then
    echo "✅ migrations/ directory exists"
    
    # Try to check current migration
    echo -n "Current migration: "
    flask db current 2>&1 || echo "❌ Failed to get current migration"
else
    echo "❌ migrations/ directory not found"
fi

# Check database connection
echo -n "Database connection: "
python -c "
from app import app, db
try:
    with app.app_context():
        db.engine.execute('SELECT 1')
        print('✅ Connected')
except Exception as e:
    print(f'❌ Failed: {e}')
" 2>&1

echo ""
echo "=== Available Commands ==="
echo ""
echo "Migration commands:"
echo "  python docker_migrate_init.py    # Initialize migrations (Docker-friendly)"
echo "  flask db current                 # Show current migration"
echo "  flask db history                 # Show migration history"
echo "  flask db upgrade                 # Apply migrations"
echo "  flask db stamp head              # Mark DB as current"
echo ""
echo "Diagnostic commands:"
echo "  python diagnose_migrations.py    # Full diagnostics"
echo "  python fix_revision_mismatch.py  # Fix revision errors"
echo "  ./quick_fix_revision.sh          # Quick revision fix"
echo ""
echo "Start application manually:"
echo "  ./startup_postgres.sh            # Normal startup"
echo "  ./startup_postgres_safe.sh       # Safe startup (won't exit)"
echo "  python app.py                    # Development server"
echo ""
echo "To exit this container:"
echo "  exit"
echo ""
echo "=== Container Ready for Debugging ==="
echo ""

# Keep container running
exec /bin/bash