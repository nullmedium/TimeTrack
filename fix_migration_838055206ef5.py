#!/usr/bin/env python3
"""
Fix the specific revision error: Can't locate revision identified by '838055206ef5'
This script will clean up the database migration state and re-initialize.
"""

import os
import sys

def main():
    """Fix the revision mismatch."""
    print("=== Fixing Revision 838055206ef5 Error ===\n")
    
    os.environ['FLASK_APP'] = 'app.py'
    
    print("This error means your database thinks it's at revision '838055206ef5'")
    print("but that revision doesn't exist in your migration files.\n")
    
    print("We'll fix this by:")
    print("1. Clearing the incorrect revision from the database")
    print("2. Re-initializing migrations from current schema")
    print("3. Marking the database as up-to-date\n")
    
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Aborting...")
        return 1
    
    # Step 1: Clear the alembic_version table
    print("\nStep 1: Clearing migration history from database...")
    try:
        from app import app, db
        with app.app_context():
            # Check if alembic_version exists
            result = db.engine.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """)
            exists = result.fetchone()[0]
            
            if exists:
                # Clear the incorrect revision
                db.engine.execute("DELETE FROM alembic_version")
                print("✓ Cleared alembic_version table")
            else:
                print("ℹ️  No alembic_version table found (this is OK)")
                
    except Exception as e:
        print(f"❌ Error clearing alembic_version: {e}")
        print("\nTry running this SQL manually:")
        print("  DELETE FROM alembic_version;")
        return 1
    
    # Step 2: Remove and recreate migrations directory
    print("\nStep 2: Re-initializing migrations...")
    
    import shutil
    if os.path.exists('migrations'):
        print("Removing old migrations directory...")
        shutil.rmtree('migrations')
    
    # Run the Docker-friendly initialization
    print("Running docker_migrate_init.py...")
    result = os.system("python docker_migrate_init.py")
    
    if result != 0:
        print("❌ Failed to initialize migrations")
        return 1
    
    # Step 3: Stamp the database
    print("\nStep 3: Marking database as current...")
    result = os.system("flask db stamp head")
    
    if result == 0:
        print("\n✅ Success! The revision error has been fixed.")
        print("\nYou can now:")
        print("1. Create new migrations: flask db migrate -m 'Your changes'")
        print("2. Apply migrations: flask db upgrade")
    else:
        print("\n⚠️  Failed to stamp database.")
        print("Try running manually: flask db stamp head")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())