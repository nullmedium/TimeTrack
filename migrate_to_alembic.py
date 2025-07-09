#!/usr/bin/env python3
"""
Special migration script to transition from manual migrations to Flask-Migrate/Alembic.
This script handles the existing database schema and creates a baseline migration.
"""

import os
import sys
import subprocess
import psycopg2
from urllib.parse import urlparse

def check_database_exists():
    """Check if database exists and has tables."""
    database_url = os.environ.get('DATABASE_URL', 'sqlite:////data/timetrack.db')
    
    if database_url.startswith('sqlite'):
        db_path = database_url.replace('sqlite:///', '')
        return os.path.exists(db_path)
    
    # PostgreSQL
    try:
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return table_count > 0
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

def run_command(cmd, description):
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
        return False

def main():
    """Main migration function."""
    print("=== Migrating to Flask-Migrate/Alembic ===")
    print("\n⚠️  IMPORTANT: This script assumes your database is at the current schema.")
    print("For baseline at commit 4214e88, use: python establish_baseline_4214e88.py")
    
    # Set Flask app
    os.environ['FLASK_APP'] = 'app.py'
    
    # Check if we have an existing database
    has_existing_db = check_database_exists()
    
    if has_existing_db:
        print("\n📊 Existing database detected!")
        print("This process will:")
        print("1. Initialize Flask-Migrate")
        print("2. Create a baseline migration matching your CURRENT schema")
        print("3. Mark the database as up-to-date without running migrations")
        print("\nThis allows you to start using Flask-Migrate for future changes.")
        print("\n⚠️  If your database is at commit 4214e88, use establish_baseline_4214e88.py instead!")
        
        response = input("\nContinue with current schema? (y/N): ")
        if response.lower() != 'y':
            print("Aborting...")
            return 1
    else:
        print("\n🆕 No existing database detected.")
        print("This will set up a fresh Flask-Migrate installation.")
    
    # Step 1: Initialize Flask-Migrate
    if not run_command("flask db init", "Initializing Flask-Migrate"):
        return 1
    
    if has_existing_db:
        # Step 2: Create initial migration from existing schema
        if not run_command(
            'flask db migrate -m "Initial migration from existing database"',
            "Creating migration from existing schema"
        ):
            return 1
        
        print("\n📝 Review the generated migration!")
        print("The migration file is in migrations/versions/")
        print("Make sure it matches your existing schema.")
        
        response = input("\nHave you reviewed the migration? Continue? (y/N): ")
        if response.lower() != 'y':
            print("Please review and run: flask db stamp head")
            return 0
        
        # Step 3: Stamp the database without running migrations
        if not run_command("flask db stamp head", "Marking database as up-to-date"):
            return 1
        
        print("\n✅ Database marked as up-to-date with current schema")
    else:
        # Fresh installation - create tables
        if not run_command(
            'flask db migrate -m "Initial database creation"',
            "Creating initial migration"
        ):
            return 1
        
        if not run_command("flask db upgrade", "Creating database tables"):
            return 1
        
        print("\n✅ Database tables created successfully")
    
    print("\n✨ Migration to Flask-Migrate completed!")
    print("\nFuture migrations:")
    print("1. Make changes to your models")
    print("2. Run: flask db migrate -m 'Description of changes'")
    print("3. Review the generated migration")
    print("4. Run: flask db upgrade")
    
    # Create a README for the team
    readme_content = """# Flask-Migrate Usage

This project now uses Flask-Migrate (Alembic) for database migrations.

## Common Commands

### Create a new migration
```bash
flask db migrate -m "Description of changes"
```

### Apply migrations
```bash
flask db upgrade
```

### View migration history
```bash
flask db history
```

### Rollback one migration
```bash
flask db downgrade
```

### View current migration
```bash
flask db current
```

## Important Notes

1. **Always review generated migrations** before applying them
2. **Test migrations** on a development database first
3. **Back up your database** before applying migrations in production
4. **Custom enums** may need manual adjustment in migration files

## Migration Files

- `migrations/` - Main migrations directory
- `migrations/versions/` - Individual migration files
- `migrations/alembic.ini` - Alembic configuration

## For Production

The startup scripts have been updated to automatically run migrations.
"""
    
    with open('migrations/README.md', 'w') as f:
        f.write(readme_content)
    
    print("\n📄 Created migrations/README.md with usage instructions")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())