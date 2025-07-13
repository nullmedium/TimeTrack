#!/usr/bin/env python
"""Check and fix migration state in the database"""

from app import app, db
from sqlalchemy import text

def check_alembic_version():
    """Check the current alembic version in the database"""
    with app.app_context():
        try:
            # Check if alembic_version table exists
            result = db.session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version'"
            ))
            
            if result.rowcount == 0:
                print("No alembic_version table found. This is a fresh database.")
                return None
                
            # Get current version
            result = db.session.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            
            if row:
                print(f"Current migration version in database: {row[0]}")
                return row[0]
            else:
                print("alembic_version table exists but is empty")
                return None
                
        except Exception as e:
            print(f"Error checking migration state: {e}")
            return None

def clean_migration_state():
    """Clean up the migration state"""
    with app.app_context():
        try:
            print("\nCleaning migration state...")
            # Drop the alembic_version table
            db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            db.session.commit()
            print("Migration state cleaned successfully!")
            return True
        except Exception as e:
            print(f"Error cleaning migration state: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("Checking migration state...")
    version = check_alembic_version()
    
    if version:
        print(f"\nThe database references migration '{version}' which doesn't exist in files.")
        response = input("Do you want to clean the migration state? (yes/no): ")
        
        if response.lower() == 'yes':
            if clean_migration_state():
                print("\nYou can now create a fresh initial migration.")
            else:
                print("\nFailed to clean migration state.")
    else:
        print("\nNo migration issues found. You can create a fresh initial migration.")