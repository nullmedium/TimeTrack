#!/usr/bin/env python3
"""
Initialize Flask-Migrate for the TimeTrack application.
This script sets up the migrations directory and creates the initial migration.
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"✗ {description} failed")
        if result.stderr:
            print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return False
    return True

def main():
    """Main initialization function."""
    print("=== Flask-Migrate Initialization ===")
    
    # Set Flask app environment variable
    os.environ['FLASK_APP'] = 'app.py'
    
    # Initialize migrations directory
    if not run_command("flask db init", "Initializing migrations directory"):
        return 1
    
    # Create initial migration
    if not run_command(
        'flask db migrate -m "Initial migration from existing schema"',
        "Creating initial migration"
    ):
        return 1
    
    print("\n✨ Flask-Migrate initialization completed!")
    print("\nNext steps:")
    print("1. Review the generated migration in migrations/versions/")
    print("2. Apply the migration with: flask db upgrade")
    print("3. For future schema changes, use: flask db migrate -m 'Description'")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())