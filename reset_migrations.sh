#!/bin/bash
# Quick reset script for migration issues

echo "=== Migration Reset Script ==="
echo ""
echo "This will completely reset your Flask-Migrate setup."
echo "Your data will NOT be affected, only migration tracking."
echo ""
read -p "Continue? (y/N): " response

if [ "$response" != "y" ]; then
    echo "Aborting..."
    exit 0
fi

export FLASK_APP=app.py

echo ""
echo "Step 1: Clearing database migration history..."
python -c "
from app import app, db
with app.app_context():
    try:
        db.engine.execute('DELETE FROM alembic_version')
        print('✓ Cleared alembic_version table')
    except Exception as e:
        print(f'⚠️  Could not clear alembic_version: {e}')
        print('   (This is OK if the table does not exist)')
"

echo ""
echo "Step 2: Removing migrations directory..."
rm -rf migrations
echo "✓ Removed migrations directory"

echo ""
echo "Step 3: Re-initializing migrations..."
flask db init
if [ $? -ne 0 ]; then
    echo "❌ Failed to initialize migrations"
    exit 1
fi
echo "✓ Initialized Flask-Migrate"

echo ""
echo "Step 4: Creating baseline migration..."
flask db migrate -m "Reset baseline migration $(date +%Y%m%d_%H%M%S)"
if [ $? -ne 0 ]; then
    echo "❌ Failed to create migration"
    exit 1
fi
echo "✓ Created baseline migration"

echo ""
echo "Step 5: Marking database as current..."
flask db stamp head
if [ $? -ne 0 ]; then
    echo "❌ Failed to stamp database"
    exit 1
fi
echo "✓ Database marked as current"

echo ""
echo "✨ Migration reset complete!"
echo ""
echo "Next steps:"
echo "1. Review the generated migration in migrations/versions/"
echo "2. Create new migrations: flask db migrate -m 'Your changes'"
echo "3. Apply migrations: flask db upgrade"