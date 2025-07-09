#!/usr/bin/env python3
"""
Fix Flask-Migrate revision mismatch errors.
Handles cases where database references a revision that doesn't exist in files.
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

def run_command(cmd, capture=True):
    """Run a command and return result."""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, shell=True)
        return result.returncode, "", ""

def get_database_revision():
    """Get current revision from database."""
    print("Checking database revision...")
    code, stdout, stderr = run_command("flask db current")
    
    if code != 0:
        if "Can't locate revision" in stderr:
            # Extract the problematic revision
            import re
            match = re.search(r"Can't locate revision identified by '([^']+)'", stderr)
            if match:
                return match.group(1), True  # revision, is_missing
        print(f"Error getting current revision: {stderr}")
        return None, False
    
    # Extract revision from output
    revision = stdout.strip().split()[0] if stdout.strip() else None
    return revision, False

def get_file_revisions():
    """Get all revisions from migration files."""
    versions_dir = Path("migrations/versions")
    if not versions_dir.exists():
        return []
    
    revisions = []
    for file in versions_dir.glob("*.py"):
        if file.name == "__pycache__":
            continue
        
        with open(file, 'r') as f:
            content = f.read()
            
        # Extract revision
        import re
        revision_match = re.search(r"^revision = ['\"]([^'\"]+)['\"]", content, re.MULTILINE)
        down_revision_match = re.search(r"^down_revision = ['\"]([^'\"]+)['\"]", content, re.MULTILINE)
        
        if revision_match:
            revisions.append({
                'file': file.name,
                'revision': revision_match.group(1),
                'down_revision': down_revision_match.group(1) if down_revision_match else None
            })
    
    return revisions

def check_alembic_version_table():
    """Check the alembic_version table directly."""
    print("\nChecking alembic_version table...")
    
    # Try to connect to database and check
    try:
        from app import app, db
        with app.app_context():
            result = db.engine.execute("SELECT version_num FROM alembic_version")
            versions = [row[0] for row in result]
            return versions
    except Exception as e:
        print(f"Could not check alembic_version table: {e}")
        return []

def main():
    """Main repair function."""
    print("=== Flask-Migrate Revision Mismatch Repair ===\n")
    
    # Set environment
    os.environ['FLASK_APP'] = 'app.py'
    
    # Step 1: Diagnose the problem
    print("Step 1: Diagnosing the issue...")
    
    db_revision, is_missing = get_database_revision()
    if is_missing:
        print(f"❌ Database references missing revision: {db_revision}")
    elif db_revision:
        print(f"📍 Current database revision: {db_revision}")
    else:
        print("⚠️  Could not determine database revision")
    
    # Step 2: Check migration files
    print("\nStep 2: Checking migration files...")
    file_revisions = get_file_revisions()
    
    if not file_revisions:
        print("❌ No migration files found!")
        print("\nSolution: Re-initialize migrations")
        print("  rm -rf migrations")
        print("  python establish_baseline_4214e88.py")
        return 1
    
    print(f"Found {len(file_revisions)} migration files:")
    for rev in file_revisions:
        print(f"  - {rev['revision'][:8]} in {rev['file']}")
    
    # Check if problematic revision exists in files
    if is_missing and db_revision:
        revision_exists = any(r['revision'] == db_revision for r in file_revisions)
        if not revision_exists:
            print(f"\n❌ Revision {db_revision} not found in migration files!")
    
    # Step 3: Check alembic_version table
    db_versions = check_alembic_version_table()
    if db_versions:
        print(f"\nDatabase alembic_version table contains: {db_versions}")
    
    # Step 4: Provide solutions
    print("\n" + "="*50)
    print("SOLUTIONS")
    print("="*50)
    
    print("\nOption 1: Reset to latest migration file (Recommended)")
    print("-" * 40)
    if file_revisions:
        latest_revision = file_revisions[-1]['revision']
        print(f"Latest revision in files: {latest_revision}")
        print("\nRun these commands:")
        print(f"  flask db stamp {latest_revision}")
        print("  flask db upgrade")
    
    print("\nOption 2: Start fresh (Nuclear option)")
    print("-" * 40)
    print("⚠️  Only do this if Option 1 fails!")
    print("\nRun these commands:")
    print("  # Clear alembic version from database")
    print("  python -c \"from app import app, db; app.app_context().push(); db.engine.execute('DELETE FROM alembic_version')\"")
    print("  # Stamp with latest revision")
    if file_revisions:
        print(f"  flask db stamp {file_revisions[-1]['revision']}")
    
    print("\nOption 3: Complete reset (Last resort)")
    print("-" * 40)
    print("⚠️  This will recreate all migrations!")
    print("\nRun these commands:")
    print("  rm -rf migrations")
    print("  python establish_baseline_4214e88.py")
    print("  flask db stamp head")
    
    # Step 5: Automated fix attempt
    print("\n" + "="*50)
    print("AUTOMATED FIX")
    print("="*50)
    
    if is_missing and file_revisions:
        response = input(f"\nAttempt to fix by stamping to latest revision? (y/N): ")
        if response.lower() == 'y':
            latest_revision = file_revisions[-1]['revision']
            print(f"\nStamping database to revision: {latest_revision}")
            code, stdout, stderr = run_command(f"flask db stamp {latest_revision}")
            
            if code == 0:
                print("✅ Successfully stamped database!")
                print("\nNow run: flask db upgrade")
            else:
                print(f"❌ Stamping failed: {stderr}")
                print("\nTry manual SQL fix:")
                print(f"  UPDATE alembic_version SET version_num = '{latest_revision}';")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())