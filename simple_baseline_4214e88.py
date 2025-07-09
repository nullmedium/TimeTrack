#!/usr/bin/env python3
"""
Simplified baseline establishment for commit 4214e88.
Handles the models.py (monolithic) to models/ (modular) transition properly.
"""

import os
import sys
import subprocess
import shutil

def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"\n➜ {description}")
    print(f"  Command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0 and check:
        print(f"❌ Command failed!")
        sys.exit(1)
    return result.returncode == 0

def main():
    """Main function."""
    print("=== Simplified Baseline Setup for Commit 4214e88 ===")
    print("\nThis script will:")
    print("1. Extract models.py from commit 4214e88")
    print("2. Create a baseline migration")
    print("3. Restore your current models structure")
    
    response = input("\nContinue? (y/N): ")
    if response.lower() != 'y':
        print("Aborting...")
        return 1
    
    # Set environment
    os.environ['FLASK_APP'] = 'app.py'
    BASELINE_COMMIT = "4214e88d18fce7a9c75927753b8d4e9222771e14"
    
    # Step 1: Clean up
    if os.path.exists('migrations'):
        print("\n⚠️  Removing existing migrations directory...")
        shutil.rmtree('migrations')
    
    # Step 2: Backup current structure
    print("\nBacking up current models...")
    if os.path.exists('models'):
        shutil.move('models', 'models_backup')
        print("✓ Backed up models/ to models_backup/")
    
    if os.path.exists('models.py'):
        shutil.move('models.py', 'models.py.backup')
        print("✓ Backed up models.py to models.py.backup")
    
    try:
        # Step 3: Get models.py from baseline commit
        print(f"\nExtracting models.py from commit {BASELINE_COMMIT[:8]}...")
        result = subprocess.run(
            f"git show {BASELINE_COMMIT}:models.py > models.py",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Failed to extract models.py from baseline commit!")
            print("Error:", result.stderr)
            return 1
        
        print("✓ Extracted models.py")
        
        # Step 4: Initialize Flask-Migrate
        print("\nInitializing Flask-Migrate...")
        run_command("flask db init", "Creating migrations directory")
        
        # Step 5: Create baseline migration
        print("\nCreating baseline migration...")
        run_command(
            'flask db migrate -m "Baseline schema from commit 4214e88"',
            "Generating migration"
        )
        
        print("✅ Baseline migration created!")
        
    finally:
        # Step 6: Always restore original structure
        print("\nRestoring original models structure...")
        
        if os.path.exists('models.py'):
            os.remove('models.py')
            print("✓ Removed temporary models.py")
        
        if os.path.exists('models.py.backup'):
            shutil.move('models.py.backup', 'models.py')
            print("✓ Restored models.py.backup")
        
        if os.path.exists('models_backup'):
            shutil.move('models_backup', 'models')
            print("✓ Restored models/ directory")
    
    # Step 7: Add note to migration
    print("\nFinalizing migration...")
    try:
        import glob
        migration_files = glob.glob('migrations/versions/*.py')
        if migration_files:
            latest = max(migration_files, key=os.path.getctime)
            
            with open(latest, 'r') as f:
                content = f.read()
            
            note = '''"""BASELINE MIGRATION FROM COMMIT 4214e88

This represents the database schema from the monolithic models.py file.
DO NOT MODIFY THIS MIGRATION.

For existing databases: flask db stamp head
For new databases: flask db upgrade
"""

'''
            with open(latest, 'w') as f:
                f.write(note + content)
            
            print(f"✓ Added baseline note to {os.path.basename(latest)}")
    except Exception as e:
        print(f"⚠️  Could not add note to migration: {e}")
    
    # Step 8: Summary
    print("\n" + "="*60)
    print("✨ SUCCESS!")
    print("="*60)
    print("\nBaseline migration created from commit 4214e88")
    print("\nNext steps:")
    print("1. For existing database: flask db stamp head")
    print("2. For new database: flask db upgrade")
    print("3. Create new migrations: flask db migrate -m 'Your changes'")
    print("\nIMPORTANT: Review the migration in migrations/versions/ before applying!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())