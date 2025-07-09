#!/usr/bin/env python3
"""
Establish Flask-Migrate baseline from git commit 4214e88d18fce7a9c75927753b8d4e9222771e14.

This script:
1. Checks out the models from commit 4214e88
2. Initializes Flask-Migrate
3. Creates an initial migration representing that schema
4. Stamps the database to mark it as up-to-date with that baseline

This allows all migrations after commit 4214e88 to be managed by Flask-Migrate.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime

def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} completed")
        if result.stdout.strip():
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

def check_git_status():
    """Ensure git working directory is clean."""
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ Git working directory is not clean!")
        print("Please commit or stash your changes before running this script.")
        return False
    return True

def get_commit_date(commit_hash):
    """Get the date of a specific commit."""
    result = subprocess.run(
        f"git show -s --format=%ci {commit_hash}",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return datetime.now().isoformat()

def main():
    """Main function to establish baseline."""
    print("=== Establishing Flask-Migrate Baseline from Commit 4214e88 ===")
    
    # Configuration
    BASELINE_COMMIT = "4214e88d18fce7a9c75927753b8d4e9222771e14"
    BASELINE_DATE = get_commit_date(BASELINE_COMMIT)
    
    print(f"Baseline commit: {BASELINE_COMMIT}")
    print(f"Commit date: {BASELINE_DATE}")
    
    # Check prerequisites
    if not check_git_status():
        return 1
    
    # Set Flask app
    os.environ['FLASK_APP'] = 'app.py'
    
    # Step 1: Clean up any existing migrations
    if os.path.exists('migrations'):
        response = input("\n⚠️  Migrations directory already exists. Remove it? (y/N): ")
        if response.lower() != 'y':
            print("Aborting...")
            return 1
        run_command("rm -rf migrations", "Removing existing migrations directory")
    
    # Step 2: Backup current models and extract baseline
    print(f"\nPreparing baseline models from commit {BASELINE_COMMIT}...")
    
    # Check if baseline commit has models.py or models/ directory
    result = subprocess.run(
        f"git show {BASELINE_COMMIT}:models.py",
        shell=True,
        capture_output=True
    )
    has_single_models_file = result.returncode == 0
    
    if has_single_models_file:
        print("✓ Found models.py in baseline commit (monolithic structure)")
        
        # Backup current models directory
        if os.path.exists('models'):
            print("Backing up current models/ directory...")
            run_command("mv models models_backup_temp", "Backing up current models")
        
        # Extract baseline models.py
        run_command(
            f"git show {BASELINE_COMMIT}:models.py > models.py",
            "Extracting baseline models.py"
        )
        
        # We need to ensure the models.py imports db correctly
        # The old file might have different imports
        print("Adjusting imports in baseline models.py...")
        with open('models.py', 'r') as f:
            content = f.read()
        
        # Ensure it has proper imports for Flask-Migrate
        if 'from flask_sqlalchemy import SQLAlchemy' not in content:
            # Add the import at the top if missing
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#'):
                    lines.insert(i, 'from flask_sqlalchemy import SQLAlchemy\ndb = SQLAlchemy()\n')
                    break
            content = '\n'.join(lines)
            
            with open('models.py', 'w') as f:
                f.write(content)
    else:
        print("⚠️  No models.py found in baseline commit")
        print("Checking for models/ directory...")
        
        # Try to check if models/ exists
        result = subprocess.run(
            f"git show {BASELINE_COMMIT}:models/__init__.py",
            shell=True,
            capture_output=True
        )
        
        if result.returncode == 0:
            print("Found models/ directory in baseline commit")
            # This shouldn't happen for commit 4214e88, but handle it anyway
            # ... existing code for models/ directory ...
        else:
            print("❌ Neither models.py nor models/ found in baseline commit!")
            print("This commit might not have SQLAlchemy models yet.")
            return 1
        
    # Step 3: Initialize Flask-Migrate
    run_command("flask db init", "Initializing Flask-Migrate")
    
    # Step 4: Create the baseline migration
    print("\n📝 Creating baseline migration...")
    print("This migration represents the schema at commit 4214e88")
    
    migration_message = f"Baseline schema from commit {BASELINE_COMMIT[:8]} ({BASELINE_DATE})"
    
    # Need to temporarily update app.py imports if using old models.py
    if has_single_models_file:
        print("Temporarily adjusting app.py imports...")
        with open('app.py', 'r') as f:
            app_content = f.read()
        
        # Replace models imports temporarily
        app_content_backup = app_content
        app_content = app_content.replace(
            'from models import db,',
            'from models import db,'
        ).replace(
            'from models import',
            'from models import'
        )
        
        with open('app.py', 'w') as f:
            f.write(app_content)
    
    # Generate the migration
    result = run_command(
        f'flask db migrate -m "{migration_message}"',
        "Generating baseline migration"
    )
    
    # Step 5: Restore current models structure
    if has_single_models_file:
        print("\nRestoring current models structure...")
        
        # Remove temporary models.py
        if os.path.exists('models.py'):
            os.remove('models.py')
            print("✓ Removed temporary models.py")
        
        # Restore models directory
        if os.path.exists('models_backup_temp'):
            run_command("mv models_backup_temp models", "Restoring models directory")
        
        # Restore app.py if we modified it
        if 'app_content_backup' in locals():
            with open('app.py', 'w') as f:
                f.write(app_content_backup)
            print("✓ Restored app.py")
    
    # Step 6: Add a note to the migration file
    migration_files = os.listdir("migrations/versions")
    if migration_files:
        latest_migration = sorted(migration_files)[-1]
        migration_path = os.path.join("migrations/versions", latest_migration)
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Add comment at the top of the file
        baseline_note = f'''"""
BASELINE MIGRATION - DO NOT MODIFY

This migration represents the database schema at commit {BASELINE_COMMIT}.
Date: {BASELINE_DATE}

This is the starting point for Flask-Migrate. All future schema changes
should be managed through Flask-Migrate migrations.

If you have a database that was created before this point, you should:
1. Ensure your database schema matches this migration
2. Run: flask db stamp head

If you're creating a new database:
1. Run: flask db upgrade
"""

'''
        
        with open(migration_path, 'w') as f:
            f.write(baseline_note + content)
        
        print(f"✓ Added baseline note to migration: {latest_migration}")
    
    # Step 7: Create documentation
    doc_content = f"""# Flask-Migrate Baseline Information

## Baseline Commit
- Commit: {BASELINE_COMMIT}
- Date: {BASELINE_DATE}
- Description: This is the baseline schema for Flask-Migrate

## For Existing Databases

If your database was created from the schema at or after commit {BASELINE_COMMIT[:8]}:

```bash
# Mark your database as being at the baseline
flask db stamp head
```

## For New Databases

```bash
# Create all tables from the baseline
flask db upgrade
```

## Post-Baseline Migrations

All migrations after commit {BASELINE_COMMIT[:8]} that were previously in the
old migration system need to be recreated as Flask-Migrate migrations:

1. Company settings additions
2. User preferences columns
3. Dashboard widget updates
4. Work configuration changes
5. Note sharing functionality
6. Time preferences

Use `flask db migrate -m "description"` to create these migrations.

## Important Notes

- Do NOT modify the baseline migration
- Always review generated migrations before applying
- Test migrations on a development database first
"""
    
    with open('migrations/BASELINE_INFO.md', 'w') as f:
        f.write(doc_content)
    
    print("\n✅ Created migrations/BASELINE_INFO.md")
    
    # Step 8: Show summary
    print("\n" + "="*60)
    print("✨ Baseline establishment completed!")
    print("="*60)
    print(f"\nBaseline: Commit {BASELINE_COMMIT[:8]} ({BASELINE_DATE})")
    print("\nNext steps:")
    print("\n1. For existing databases at or after this commit:")
    print("   flask db stamp head")
    print("\n2. For new databases:")
    print("   flask db upgrade")
    print("\n3. To add post-baseline changes:")
    print("   - Review migrations_old/postgres_only_migration.py")
    print("   - Create new migrations for changes after 4214e88")
    print("   - Example: flask db migrate -m 'Add company settings columns'")
    print("\n4. Always review generated migrations in migrations/versions/")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())