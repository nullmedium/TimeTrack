#!/usr/bin/env python
"""Create a new migration with Flask-Migrate"""

import os
import sys
from flask_migrate import migrate as _migrate
from app import app, db

if __name__ == '__main__':
    with app.app_context():
        print("Creating migration...")
        try:
            # Get migration message from command line or use default
            message = sys.argv[1] if len(sys.argv) > 1 else "Initial migration"
            
            # Create the migration
            _migrate(message=message)
            print(f"Migration '{message}' created successfully!")
            print("Review the migration file in migrations/versions/")
            print("To apply the migration, run: python apply_migration.py")
        except Exception as e:
            print(f"Error creating migration: {e}")
            sys.exit(1)