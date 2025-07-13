#!/usr/bin/env python
"""Test script to verify Flask-Migrate setup"""

from app import app, db, migrate
from flask_migrate import init, migrate as _migrate, upgrade

with app.app_context():
    print("Flask app created successfully")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Migrate instance: {migrate}")
    print(f"Available commands: {app.cli.commands}")
    
    # Check if 'db' command is registered
    if 'db' in app.cli.commands:
        print("'db' command is registered!")
        print(f"Subcommands: {list(app.cli.commands['db'].commands.keys())}")
    else:
        print("ERROR: 'db' command is NOT registered!")
        print(f"Available commands: {list(app.cli.commands.keys())}")