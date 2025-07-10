#!/usr/bin/env python
"""Clean migration state and handle orphaned tables"""

from app import app, db
from sqlalchemy import text

def get_all_tables():
    """Get all tables in the database"""
    with app.app_context():
        result = db.session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ))
        return [row[0] for row in result]

def check_migration_state():
    """Check current migration state"""
    with app.app_context():
        try:
            result = db.session.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            if row:
                print(f"Current migration version: {row[0]}")
                return row[0]
        except:
            print("No alembic_version table found")
        return None

def clean_migration_only():
    """Clean only the migration state, keep all other tables"""
    with app.app_context():
        try:
            print("Cleaning migration state only...")
            db.session.execute(text("DELETE FROM alembic_version"))
            db.session.commit()
            print("Migration state cleaned successfully!")
            return True
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
            return False

def list_orphaned_tables():
    """List tables that exist in DB but not in models"""
    with app.app_context():
        all_tables = get_all_tables()
        
        # Get tables from current models
        model_tables = set()
        for table in db.metadata.tables.values():
            model_tables.add(table.name)
        
        # Find orphaned tables
        orphaned = []
        for table in all_tables:
            if table not in model_tables and table != 'alembic_version':
                orphaned.append(table)
        
        return orphaned

if __name__ == '__main__':
    print("=== Migration State Check ===")
    
    # Check current state
    version = check_migration_state()
    
    # List all tables
    print("\n=== Database Tables ===")
    tables = get_all_tables()
    for table in sorted(tables):
        print(f"  - {table}")
    
    # Check for orphaned tables
    orphaned = list_orphaned_tables()
    if orphaned:
        print("\n=== Orphaned Tables (not in current models) ===")
        for table in sorted(orphaned):
            print(f"  - {table}")
        print("\nThese tables exist in the database but are not defined in your current models.")
        print("They might be from old features or previous schema versions.")
    
    if version:
        print(f"\n=== Action Required ===")
        print(f"The database has migration '{version}' but no migration files exist.")
        print("\nOptions:")
        print("1. Clean migration state only (keeps all tables)")
        print("2. Cancel and handle manually")
        
        choice = input("\nEnter your choice (1 or 2): ")
        
        if choice == '1':
            if clean_migration_only():
                print("\n✓ Migration state cleaned!")
                print("You can now run: python create_migration.py")
        else:
            print("\nCancelled. No changes made.")