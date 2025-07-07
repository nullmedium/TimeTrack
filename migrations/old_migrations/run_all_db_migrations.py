#!/usr/bin/env python3
"""
Master database migration runner
Runs all database schema migrations in the correct order
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# Migration state file
MIGRATION_STATE_FILE = '/data/db_migrations_state.json'

# List of database schema migrations in order
DB_MIGRATIONS = [
    '01_migrate_db.py',  # SQLite schema updates (must run before data migration)
    '20_add_company_updated_at.py',  # Add updated_at column BEFORE data migration
    '02_migrate_sqlite_to_postgres_fixed.py',  # Fixed SQLite to PostgreSQL data migration
    '03_add_dashboard_columns.py',
    '04_add_user_preferences_columns.py',
    '05_fix_task_status_enum.py',
    '06_add_archived_status.py',
    '07_fix_company_work_config_columns.py',
    '08_fix_work_region_enum.py',
    '09_add_germany_to_workregion.py',
    '10_add_company_settings_columns.py',
    '19_add_company_invitations.py'
]

def load_migration_state():
    """Load the migration state from file"""
    if os.path.exists(MIGRATION_STATE_FILE):
        try:
            with open(MIGRATION_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_migration_state(state):
    """Save the migration state to file"""
    os.makedirs(os.path.dirname(MIGRATION_STATE_FILE), exist_ok=True)
    with open(MIGRATION_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def run_migration(migration_file):
    """Run a single migration script"""
    script_path = os.path.join(os.path.dirname(__file__), migration_file)
    
    if not os.path.exists(script_path):
        print(f"⚠️  Migration {migration_file} not found, skipping...")
        return False
    
    print(f"\n🔄 Running migration: {migration_file}")
    
    try:
        # Run the migration script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {migration_file} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {migration_file} failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            if result.stdout:
                print(f"Standard output: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {migration_file}: {e}")
        return False

def main():
    """Run all database migrations"""
    print("=== Database Schema Migrations ===")
    print(f"Running {len(DB_MIGRATIONS)} migrations...")
    
    # Load migration state
    state = load_migration_state()
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for migration in DB_MIGRATIONS:
        # Check if migration has already been run successfully
        if state.get(migration, {}).get('status') == 'success':
            print(f"\n⏭️  Skipping {migration} (already completed)")
            skipped_count += 1
            continue
        
        # Run the migration
        success = run_migration(migration)
        
        # Update state
        state[migration] = {
            'status': 'success' if success else 'failed',
            'timestamp': datetime.now().isoformat(),
            'attempts': state.get(migration, {}).get('attempts', 0) + 1
        }
        
        if success:
            success_count += 1
        else:
            failed_count += 1
            # Don't stop on failure, continue with other migrations
            print(f"⚠️  Continuing despite failure in {migration}")
        
        # Save state after each migration
        save_migration_state(state)
    
    # Summary
    print("\n" + "="*50)
    print("Database Migration Summary:")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"📊 Total: {len(DB_MIGRATIONS)}")
    
    if failed_count > 0:
        print("\n⚠️  Some migrations failed. Check the logs above for details.")
        return 1
    else:
        print("\n✨ All database migrations completed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())