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

# Check if SQLite database exists and has data
SQLITE_PATH="/data/timetrack.db"
if [ -f "$SQLITE_PATH" ]; then
    echo "SQLite database found at $SQLITE_PATH"
    
    # Check if PostgreSQL database is empty
    POSTGRES_TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    
    if [ "$POSTGRES_TABLE_COUNT" -eq 0 ]; then
        echo "PostgreSQL database is empty, running migration..."
        
        # Create a backup of SQLite database
        cp "$SQLITE_PATH" "${SQLITE_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "Created SQLite backup"
        
        # Run migration
        python migrate_sqlite_to_postgres.py
        
        if [ $? -eq 0 ]; then
            echo "Migration completed successfully!"
            
            # Rename SQLite database to indicate it's been migrated
            mv "$SQLITE_PATH" "${SQLITE_PATH}.migrated"
            echo "SQLite database renamed to indicate migration completion"
        else
            echo "Migration failed! Check migration.log for details"
            exit 1
        fi
    else
        echo "PostgreSQL database already contains tables, skipping migration"
    fi
else
    echo "No SQLite database found, starting with fresh PostgreSQL database"
fi

# Initialize database tables if they don't exist
echo "Ensuring database tables exist..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created/verified')
"

# Start the Flask application with gunicorn
echo "Starting Flask application with gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 30 app:app