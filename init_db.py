#!/usr/bin/env python
"""Initialize the database migrations manually"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////data/timetrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create db and migrate instances
db = SQLAlchemy(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        print("Initializing migration repository...")
        try:
            init()
            print("Migration repository initialized successfully!")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)