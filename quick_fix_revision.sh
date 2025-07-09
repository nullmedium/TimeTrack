#!/bin/bash
# Quick fix for revision mismatch error

echo "=== Quick Fix for Revision 838055206ef5 Error ==="
echo ""
echo "This error occurs when the database references a migration that doesn't exist."
echo "We'll fix this by resetting to the current migration files."
echo ""

# Set Flask app
export FLASK_APP=app.py

# Show current situation
echo "Current migration files:"
ls -la migrations/versions/*.py 2>/dev/null || echo "No migration files found!"

echo ""
echo "Attempting to get current database state:"
flask db current 2>&1 || true

echo ""
echo "Available options:"
echo "1. Reset to latest migration file (safest)"
echo "2. Clear migration history and start fresh"
echo "3. Cancel and investigate manually"
echo ""
read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Finding latest migration..."
        # Get the latest migration revision
        latest_revision=$(ls -t migrations/versions/*.py 2>/dev/null | head -1 | xargs grep "^revision = " | cut -d"'" -f2)
        
        if [ -z "$latest_revision" ]; then
            echo "❌ No migration files found!"
            echo "Run: python establish_baseline_4214e88.py"
            exit 1
        fi
        
        echo "Latest revision: $latest_revision"
        echo "Stamping database to this revision..."
        
        flask db stamp $latest_revision
        
        if [ $? -eq 0 ]; then
            echo "✅ Success! Database stamped to $latest_revision"
            echo ""
            echo "Next steps:"
            echo "1. Run: flask db upgrade"
            echo "2. Then you can create new migrations"
        else
            echo "❌ Stamping failed. Try option 2."
        fi
        ;;
        
    2)
        echo ""
        echo "⚠️  This will clear all migration history!"
        read -p "Are you sure? (y/N): " confirm
        
        if [ "$confirm" = "y" ]; then
            echo "Clearing alembic_version table..."
            python -c "
from app import app, db
with app.app_context():
    try:
        db.engine.execute('DELETE FROM alembic_version')
        print('✅ Cleared alembic_version table')
    except Exception as e:
        print(f'❌ Error: {e}')
"
            
            echo ""
            echo "Now re-establishing baseline..."
            python establish_baseline_4214e88.py
            
            if [ $? -eq 0 ]; then
                flask db stamp head
                echo "✅ Migration state reset successfully!"
            fi
        else
            echo "Cancelled."
        fi
        ;;
        
    3)
        echo "Cancelled. Run 'python fix_revision_mismatch.py' for detailed diagnostics."
        ;;
        
    *)
        echo "Invalid option"
        ;;
esac