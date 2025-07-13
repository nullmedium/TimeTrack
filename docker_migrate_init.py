#!/usr/bin/env python3
"""
Docker-friendly Flask-Migrate initialization.
No Git required - works with current schema as baseline.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"\n➜ {description}")
    print(f"  Command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Success")
        if result.stdout.strip():
            print(f"  {result.stdout.strip()}")
        return True
    else:
        print(f"✗ Failed")
        if result.stderr:
            print(f"  Error: {result.stderr}")
        if check:
            sys.exit(1)
        return False

def check_database_connection():
    """Check if we can connect to the database."""
    print("\nChecking database connection...")
    try:
        from app import app, db
        with app.app_context():
            # Try a simple query
            db.engine.execute("SELECT 1")
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_existing_tables():
    """Check what tables exist in the database."""
    print("\nChecking existing tables...")
    try:
        from app import app, db
        with app.app_context():
            # Get table names
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if tables:
                print(f"✓ Found {len(tables)} existing tables:")
                for table in sorted(tables):
                    if table != 'alembic_version':
                        print(f"  - {table}")
                return True
            else:
                print("ℹ️  No tables found (empty database)")
                return False
    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False

def main():
    """Main initialization function."""
    print("=== Flask-Migrate Docker Initialization ===")
    print("\nThis script will set up Flask-Migrate for your Docker deployment.")
    print("It uses your CURRENT schema as the baseline (no Git required).")
    
    # Set environment
    os.environ['FLASK_APP'] = 'app.py'
    
    # Check prerequisites
    if not check_database_connection():
        print("\n❌ Cannot connect to database. Check your DATABASE_URL.")
        return 1
    
    has_tables = check_existing_tables()
    
    print("\n" + "="*50)
    if has_tables:
        print("SCENARIO: Existing database with tables")
        print("="*50)
        print("\nYour database already has tables. We'll create a baseline")
        print("migration and mark it as already applied.")
    else:
        print("SCENARIO: Empty database")
        print("="*50)
        print("\nYour database is empty. We'll create a baseline")
        print("migration that can be applied to create all tables.")
    
    response = input("\nContinue? (y/N): ")
    if response.lower() != 'y':
        print("Aborting...")
        return 1
    
    # Step 1: Clean up any existing migrations
    if os.path.exists('migrations'):
        print("\n⚠️  Removing existing migrations directory...")
        shutil.rmtree('migrations')
    
    # Step 2: Initialize Flask-Migrate
    print("\nInitializing Flask-Migrate...")
    if not run_command("flask db init", "Creating migrations directory"):
        return 1
    
    # Step 3: Create baseline migration
    print("\nCreating baseline migration from current models...")
    baseline_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not run_command(
        f'flask db migrate -m "Docker baseline migration - {baseline_date}"',
        "Generating migration"
    ):
        return 1
    
    # Step 4: Add documentation to the migration
    print("\nDocumenting the migration...")
    try:
        import glob
        migration_files = glob.glob('migrations/versions/*.py')
        if migration_files:
            latest = max(migration_files, key=os.path.getctime)
            
            with open(latest, 'r') as f:
                content = f.read()
            
            note = f'''"""DOCKER BASELINE MIGRATION
Generated: {baseline_date}

This migration represents the current state of your models.
It serves as the baseline for all future migrations.

For existing databases with tables:
  flask db stamp head  # Mark as current without running

For new empty databases:
  flask db upgrade     # Create all tables

DO NOT MODIFY THIS MIGRATION
"""

'''
            with open(latest, 'w') as f:
                f.write(note + content)
            
            print(f"✓ Documented {os.path.basename(latest)}")
    except Exception as e:
        print(f"⚠️  Could not document migration: {e}")
    
    # Step 5: Handle based on database state
    print("\n" + "="*50)
    print("NEXT STEPS")
    print("="*50)
    
    if has_tables:
        print("\nYour database already has tables. Run this command to")
        print("mark it as up-to-date WITHOUT running the migration:")
        print("\n  flask db stamp head")
        print("\nThen you can create new migrations normally:")
        print("  flask db migrate -m 'Add new feature'")
        print("  flask db upgrade")
    else:
        print("\nYour database is empty. Run this command to")
        print("create all tables from the baseline migration:")
        print("\n  flask db upgrade")
        print("\nThen you can create new migrations normally:")
        print("  flask db migrate -m 'Add new feature'")
        print("  flask db upgrade")
    
    # Create a helper script
    helper_content = f"""#!/bin/bash
# Flask-Migrate helper for Docker
# Generated: {baseline_date}

export FLASK_APP=app.py

case "$1" in
    status)
        echo "Current migration status:"
        flask db current
        ;;
    
    apply)
        echo "Applying pending migrations..."
        flask db upgrade
        ;;
    
    create)
        if [ -z "$2" ]; then
            echo "Usage: $0 create 'Migration message'"
            exit 1
        fi
        echo "Creating new migration: $2"
        flask db migrate -m "$2"
        echo "Review the migration, then run: $0 apply"
        ;;
    
    mark-current)
        echo "Marking database as current (no changes)..."
        flask db stamp head
        ;;
    
    *)
        echo "Flask-Migrate Docker Helper"
        echo "Usage:"
        echo "  $0 status        - Show current migration status"
        echo "  $0 apply         - Apply pending migrations"
        echo "  $0 create 'msg'  - Create new migration"
        echo "  $0 mark-current  - Mark DB as current (existing DBs)"
        ;;
esac
"""
    
    with open('migrate.sh', 'w') as f:
        f.write(helper_content)
    
    os.chmod('migrate.sh', 0o755)
    print("\n✓ Created migrate.sh helper script")
    
    print("\n✨ Initialization complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())