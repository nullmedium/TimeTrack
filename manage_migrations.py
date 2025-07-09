#!/usr/bin/env python3
"""
Migration management script for TimeTrack.
Handles both development and production migration scenarios.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} completed")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"✗ {description} failed")
        if result.stderr:
            print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if check:
            sys.exit(1)
        return False

def init_migrations():
    """Initialize Flask-Migrate."""
    os.environ['FLASK_APP'] = 'app.py'
    
    if os.path.exists('migrations'):
        print("⚠️  Migrations directory already exists!")
        response = input("Do you want to reinitialize? This will delete existing migrations. (y/N): ")
        if response.lower() != 'y':
            print("Aborting...")
            return False
        run_command("rm -rf migrations", "Removing existing migrations directory")
    
    run_command("flask db init", "Initializing Flask-Migrate")
    return True

def create_migration(message):
    """Create a new migration."""
    os.environ['FLASK_APP'] = 'app.py'
    
    if not message:
        message = input("Enter migration message: ")
    
    run_command(f'flask db migrate -m "{message}"', "Creating migration")
    print("\n📝 Please review the generated migration before applying it!")
    return True

def apply_migrations():
    """Apply pending migrations."""
    os.environ['FLASK_APP'] = 'app.py'
    
    # Show current version
    run_command("flask db current", "Current database version", check=False)
    
    # Show pending migrations
    print("\nPending migrations:")
    run_command("flask db show", "Migration history", check=False)
    
    response = input("\nApply pending migrations? (y/N): ")
    if response.lower() == 'y':
        run_command("flask db upgrade", "Applying migrations")
    return True

def rollback_migration():
    """Rollback to previous migration."""
    os.environ['FLASK_APP'] = 'app.py'
    
    run_command("flask db current", "Current database version")
    response = input("\nRollback to previous version? (y/N): ")
    
    if response.lower() == 'y':
        run_command("flask db downgrade", "Rolling back migration")
    return True

def show_history():
    """Show migration history."""
    os.environ['FLASK_APP'] = 'app.py'
    
    run_command("flask db history", "Migration history")
    return True

def stamp_database(revision='head'):
    """Stamp database with a specific revision without running migrations."""
    os.environ['FLASK_APP'] = 'app.py'
    
    print(f"⚠️  This will mark the database as being at revision '{revision}' without running any migrations.")
    response = input("Continue? (y/N): ")
    
    if response.lower() == 'y':
        run_command(f"flask db stamp {revision}", f"Stamping database with revision {revision}")
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Manage Flask-Migrate migrations')
    parser.add_argument('command', choices=['init', 'create', 'apply', 'rollback', 'history', 'stamp'],
                        help='Command to execute')
    parser.add_argument('-m', '--message', help='Migration message (for create command)')
    parser.add_argument('-r', '--revision', default='head', help='Revision to stamp (for stamp command)')
    
    args = parser.parse_args()
    
    commands = {
        'init': init_migrations,
        'create': lambda: create_migration(args.message),
        'apply': apply_migrations,
        'rollback': rollback_migration,
        'history': show_history,
        'stamp': lambda: stamp_database(args.revision)
    }
    
    print(f"=== TimeTrack Migration Manager ===")
    print(f"Command: {args.command}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = commands[args.command]()
    
    if success:
        print("\n✨ Operation completed successfully!")
    else:
        print("\n❌ Operation failed or was cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()