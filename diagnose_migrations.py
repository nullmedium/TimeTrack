#!/usr/bin/env python3
"""
Diagnostic script for Flask-Migrate issues.
Helps identify common problems with migrations.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, capture=True):
    """Run a command and return result."""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd, shell=True).returncode, "", ""

def check_environment():
    """Check environment setup."""
    print("=== Environment Check ===")
    
    # Check FLASK_APP
    flask_app = os.environ.get('FLASK_APP', 'Not set')
    print(f"FLASK_APP: {flask_app}")
    if flask_app == 'Not set':
        print("  ⚠️  FLASK_APP not set. Setting to app.py")
        os.environ['FLASK_APP'] = 'app.py'
    
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL', 'Not set')
    if db_url != 'Not set':
        # Hide password in output
        if '@' in db_url:
            parts = db_url.split('@')
            proto_user = parts[0].split('://')
            if len(proto_user) > 1 and ':' in proto_user[1]:
                user_pass = proto_user[1].split(':')
                safe_url = f"{proto_user[0]}://{user_pass[0]}:****@{parts[1]}"
            else:
                safe_url = db_url
        else:
            safe_url = db_url
        print(f"DATABASE_URL: {safe_url}")
    else:
        print("DATABASE_URL: Using default from app.py")
    
    print()

def check_migrations_directory():
    """Check migrations directory structure."""
    print("=== Migrations Directory Check ===")
    
    if not os.path.exists('migrations'):
        print("❌ migrations/ directory not found!")
        print("  Run: python establish_baseline_4214e88.py")
        return False
    
    print("✓ migrations/ directory exists")
    
    # Check for required files
    required_files = ['alembic.ini', 'env.py', 'script.py.mako']
    for file in required_files:
        path = os.path.join('migrations', file)
        if os.path.exists(path):
            print(f"✓ {file} exists")
        else:
            print(f"❌ {file} missing!")
            return False
    
    # Check versions directory
    versions_dir = os.path.join('migrations', 'versions')
    if not os.path.exists(versions_dir):
        print("❌ versions/ directory missing!")
        return False
    
    print("✓ versions/ directory exists")
    
    # List migration files
    migration_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
    print(f"\nMigration files found: {len(migration_files)}")
    for f in sorted(migration_files):
        print(f"  - {f}")
    
    print()
    return True

def check_database_state():
    """Check current database migration state."""
    print("=== Database State Check ===")
    
    # Check current revision
    code, stdout, stderr = run_command("flask db current")
    if code == 0:
        print(f"Current revision: {stdout.strip()}")
    else:
        print("❌ Failed to get current revision")
        print(f"Error: {stderr}")
        return False
    
    # Check if database is up to date
    code, stdout, stderr = run_command("flask db check")
    if code == 0:
        if "Database is up to date" in stdout:
            print("✓ Database is up to date")
        else:
            print("⚠️  Database may need upgrade")
            print(stdout)
    else:
        print("⚠️  Database check returned non-zero")
        if stderr:
            print(f"Error: {stderr}")
    
    print()
    return True

def check_model_imports():
    """Check if models can be imported."""
    print("=== Model Import Check ===")
    
    try:
        from app import app, db
        print("✓ Successfully imported app and db")
        
        with app.app_context():
            # Try to import all models
            from models import (
                Company, User, Project, Task, TimeEntry,
                CompanySettings, UserPreferences, Sprint
            )
            print("✓ Successfully imported all main models")
            
            # Check if models have tables
            print("\nModel tables:")
            for model in [Company, User, Project, Task, TimeEntry]:
                table_name = model.__tablename__
                print(f"  - {model.__name__}: {table_name}")
    
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    return True

def test_migration_detection():
    """Test if Flask-Migrate can detect changes."""
    print("=== Migration Detection Test ===")
    
    # Try a dry run
    code, stdout, stderr = run_command("flask db migrate --dry-run")
    
    if code == 0:
        if "No changes in schema detected" in stdout:
            print("ℹ️  No schema changes detected")
            print("  This means your models match the current migration state")
        else:
            print("✓ Flask-Migrate can detect changes")
            print("\nDetected changes:")
            print(stdout)
    else:
        print("❌ Migration detection failed")
        if "Target database is not up to date" in stderr:
            print("  ⚠️  Database needs upgrade first!")
            print("  Run: flask db upgrade")
        else:
            print(f"Error: {stderr}")
    
    print()

def suggest_fixes():
    """Suggest fixes based on diagnostics."""
    print("=== Suggested Actions ===")
    
    # Check if we need to upgrade
    code, stdout, stderr = run_command("flask db heads")
    if code == 0:
        heads = stdout.strip()
        code2, current, _ = run_command("flask db current")
        if code2 == 0 and current.strip() != heads:
            print("1. Your database is not at the latest migration:")
            print("   flask db upgrade")
            print()
    
    # Check for pending migrations
    code, stdout, stderr = run_command("flask db show")
    if code == 0 and "pending upgrade" in stdout.lower():
        print("2. You have pending migrations to apply:")
        print("   flask db upgrade")
        print()
    
    print("3. To create a new migration after making model changes:")
    print("   flask db migrate -m 'Description of changes'")
    print("   flask db upgrade")
    print()
    
    print("4. If you're getting 'No changes detected':")
    print("   - Ensure you've actually modified a model")
    print("   - Check that the model is imported in models/__init__.py")
    print("   - Try comparing with: flask db compare")
    print()
    
    print("5. For 'Target database is not up to date' errors:")
    print("   flask db stamp head  # Force mark as current")
    print("   flask db migrate -m 'Your changes'")
    print()

def main():
    """Run all diagnostics."""
    print("=== Flask-Migrate Diagnostic Tool ===\n")
    
    # Run checks
    check_environment()
    
    if not check_migrations_directory():
        print("\n❌ Migrations not properly initialized")
        print("Run: python establish_baseline_4214e88.py")
        return 1
    
    if not check_model_imports():
        print("\n❌ Model import issues detected")
        return 1
    
    check_database_state()
    test_migration_detection()
    suggest_fixes()
    
    print("=== Diagnostic Complete ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())