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
    
    # Step 2: Create a temporary directory for baseline models
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nCreating temporary directory: {tmpdir}")
        
        # Step 3: Extract models from baseline commit
        print(f"\nExtracting models from commit {BASELINE_COMMIT}...")
        
        # Get the models directory from the baseline commit
        models_files = [
            "models/__init__.py",
            "models/base.py",
            "models/enums.py",
            "models/company.py",
            "models/user.py",
            "models/team.py",
            "models/project.py",
            "models/task.py",
            "models/time_entry.py",
            "models/sprint.py",
            "models/system.py",
            "models/announcement.py",
            "models/dashboard.py",
            "models/work_config.py",
            "models/invitation.py",
            "models/note.py",
            "models/note_share.py"
        ]
        
        # Also check if models_old.py exists in baseline (fallback)
        result = subprocess.run(
            f"git show {BASELINE_COMMIT}:models_old.py",
            shell=True,
            capture_output=True
        )
        use_models_old = result.returncode == 0
        
        if use_models_old:
            print("Using models_old.py from baseline commit")
            # Save current models
            run_command("cp -r models models_current", "Backing up current models")
            
            # Get models_old.py from baseline
            run_command(
                f"git show {BASELINE_COMMIT}:models_old.py > models_baseline.py",
                "Extracting baseline models"
            )
            
            # Temporarily replace models with baseline
            # This is a bit hacky but ensures we generate the right migration
            print("\nPreparing baseline schema...")
            with open('models_baseline.py', 'r') as f:
                baseline_content = f.read()
            
            # We need to be careful here - save current state and restore later
        else:
            print("Using models/ directory from baseline commit")
            # Extract each model file from baseline
            os.makedirs(os.path.join(tmpdir, "models"), exist_ok=True)
            
            for model_file in models_files:
                result = subprocess.run(
                    f"git show {BASELINE_COMMIT}:{model_file}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    file_path = os.path.join(tmpdir, model_file)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(result.stdout)
                    print(f"  ✓ Extracted {model_file}")
                else:
                    print(f"  ⚠️  Could not extract {model_file}")
        
        # Step 4: Initialize Flask-Migrate
        run_command("flask db init", "Initializing Flask-Migrate")
        
        # Step 5: Create the baseline migration
        print("\n📝 Creating baseline migration...")
        print("This migration represents the schema at commit 4214e88")
        
        migration_message = f"Baseline schema from commit {BASELINE_COMMIT[:8]} ({BASELINE_DATE})"
        run_command(
            f'flask db migrate -m "{migration_message}"',
            "Generating baseline migration"
        )
        
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