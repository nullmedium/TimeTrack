#!/usr/bin/env python3
"""
Fix common Flask-Migrate sequencing issues.
Handles the case where you need to apply migrations before creating new ones.
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a command with output."""
    print(f"\n➜ {description}")
    print(f"  Command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def main():
    """Fix migration sequence issues."""
    print("=== Flask-Migrate Sequence Fix ===")
    
    # Set environment
    os.environ['FLASK_APP'] = 'app.py'
    
    print("\nThis script will:")
    print("1. Show current migration status")
    print("2. Apply any pending migrations")
    print("3. Prepare for creating new migrations")
    
    input("\nPress Enter to continue...")
    
    # Step 1: Show current status
    print("\n" + "="*50)
    print("STEP 1: Current Status")
    print("="*50)
    
    run_command("flask db current", "Current database revision")
    run_command("flask db heads", "Latest migration in files")
    
    # Step 2: Check if upgrade needed
    print("\n" + "="*50)
    print("STEP 2: Checking for pending migrations")
    print("="*50)
    
    # Try to upgrade
    if run_command("flask db upgrade", "Applying pending migrations"):
        print("✅ Database is now up to date")
    else:
        print("⚠️  Upgrade failed. Trying to fix...")
        
        # Try stamping head
        response = input("\nStamp database as current? (y/N): ")
        if response.lower() == 'y':
            if run_command("flask db stamp head", "Stamping database"):
                print("✅ Database stamped as current")
    
    # Step 3: Test creating a migration
    print("\n" + "="*50)
    print("STEP 3: Testing migration creation")
    print("="*50)
    
    if run_command("flask db migrate --dry-run", "Dry run of migration"):
        print("✅ Ready to create new migrations")
        print("\nYou can now run:")
        print("  flask db migrate -m 'Your migration message'")
    else:
        print("❌ Still having issues")
        print("\nTry running: python diagnose_migrations.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())