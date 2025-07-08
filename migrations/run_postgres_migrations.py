#!/usr/bin/env python3
"""
PostgreSQL-only migration runner
Manages migration state and runs migrations in order
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Migration state file
MIGRATION_STATE_FILE = '/data/postgres_migrations_state.json'

# List of PostgreSQL migrations in order
POSTGRES_MIGRATIONS = [
    'postgres_only_migration.py',  # Main migration from commit 4214e88 onward
    'add_note_sharing.sql',  # Add note sharing functionality
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
        # Check if it's a SQL file
        if migration_file.endswith('.sql'):
            # Run SQL file using psql
            # Try to parse DATABASE_URL first, fall back to individual env vars
            database_url = os.environ.get('DATABASE_URL')
            if database_url:
                # Parse DATABASE_URL: postgresql://user:password@host:port/dbname
                from urllib.parse import urlparse
                parsed = urlparse(database_url)
                db_host = parsed.hostname or 'db'
                db_port = parsed.port or 5432
                db_name = parsed.path.lstrip('/') or 'timetrack'
                db_user = parsed.username or 'timetrack'
                db_password = parsed.password or 'timetrack'
            else:
                db_host = os.environ.get('POSTGRES_HOST', 'db')
                db_name = os.environ.get('POSTGRES_DB', 'timetrack')
                db_user = os.environ.get('POSTGRES_USER', 'timetrack')
                db_password = os.environ.get('POSTGRES_PASSWORD', 'timetrack')
            
            result = subprocess.run(
                ['psql', '-h', db_host, '-U', db_user, '-d', db_name, '-f', script_path],
                capture_output=True,
                text=True,
                env={**os.environ, 'PGPASSWORD': db_password}
            )
        else:
            # Run Python migration script
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
    """Run all PostgreSQL migrations"""
    print("=== PostgreSQL Database Migrations ===")
    print(f"Running {len(POSTGRES_MIGRATIONS)} migrations...")
    
    # Load migration state
    state = load_migration_state()
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for migration in POSTGRES_MIGRATIONS:
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
        
        # Save state after each migration
        save_migration_state(state)
    
    # Summary
    print("\n" + "="*50)
    print("PostgreSQL Migration Summary:")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"📊 Total: {len(POSTGRES_MIGRATIONS)}")
    
    if failed_count > 0:
        print("\n⚠️  Some migrations failed. Check the logs above for details.")
        return 1
    else:
        print("\n✨ All PostgreSQL migrations completed successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())