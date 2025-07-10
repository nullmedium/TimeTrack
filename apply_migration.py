#!/usr/bin/env python
"""Apply database migrations with Flask-Migrate"""

from flask_migrate import upgrade
from app import app, db

if __name__ == '__main__':
    with app.app_context():
        print("Applying migrations...")
        try:
            upgrade()
            print("Migrations applied successfully!")
        except Exception as e:
            print(f"Error applying migrations: {e}")
            import traceback
            traceback.print_exc()