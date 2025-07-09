#!/usr/bin/env python3
"""
Run code migrations during startup - updates code to match model changes
"""

import os
import sys
import subprocess
from pathlib import Path
import hashlib
import json
from datetime import datetime

MIGRATION_STATE_FILE = '/data/code_migrations_state.json'

def get_migration_hash(script_path):
    """Get hash of migration script to detect changes"""
    with open(script_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def load_migration_state():
    """Load state of previously run migrations"""
    if os.path.exists(MIGRATION_STATE_FILE):
        try:
            with open(MIGRATION_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_migration_state(state):
    """Save migration state"""
    os.makedirs(os.path.dirname(MIGRATION_STATE_FILE), exist_ok=True)
    with open(MIGRATION_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def should_run_migration(script_path, state):
    """Check if migration should run based on state"""
    script_name = os.path.basename(script_path)
    current_hash = get_migration_hash(script_path)
    
    if script_name not in state:
        return True
    
    # Re-run if script has changed
    if state[script_name].get('hash') != current_hash:
        return True
    
    # Skip if already run successfully
    if state[script_name].get('status') == 'success':
        return False
    
    return True

def run_migration(script_path, state):
    """Run a single migration script"""
    script_name = os.path.basename(script_path)
    print(f"\n{'='*60}")
    print(f"Running code migration: {script_name}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minute timeout
        )
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        # Update state
        state[script_name] = {
            'hash': get_migration_hash(script_path),
            'status': 'success',
            'last_run': str(datetime.now()),
            'output': result.stdout[-1000:] if result.stdout else ''  # Last 1000 chars
        }
        save_migration_state(state)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}:")
        print(e.stdout)
        print(e.stderr)
        
        # Update state with failure
        state[script_name] = {
            'hash': get_migration_hash(script_path),
            'status': 'failed',
            'last_run': str(datetime.now()),
            'error': str(e)
        }
        save_migration_state(state)
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ Migration {script_name} timed out!")
        state[script_name] = {
            'hash': get_migration_hash(script_path),
            'status': 'timeout',
            'last_run': str(datetime.now())
        }
        save_migration_state(state)
        return False

def main():
    """Run all code migrations that need to be run"""
    
    print("🔄 Checking for code migrations...")
    
    # Get migration state
    state = load_migration_state()
    
    # Get all migration scripts
    migrations_dir = Path(__file__).parent
    migration_scripts = sorted([
        str(p) for p in migrations_dir.glob('*.py')
        if p.name.startswith(('11_', '12_', '13_', '14_', '15_')) 
        and 'template' not in p.name.lower()
    ])
    
    if not migration_scripts:
        print("No code migration scripts found.")
        return 0
    
    # Check which migrations need to run
    to_run = []
    for script in migration_scripts:
        if should_run_migration(script, state):
            to_run.append(script)
    
    if not to_run:
        print("✅ All code migrations are up to date.")
        return 0
    
    print(f"\n📋 Found {len(to_run)} code migrations to run:")
    for script in to_run:
        print(f"  - {Path(script).name}")
    
    # Run migrations
    failed = []
    for script in to_run:
        if not run_migration(script, state):
            failed.append(script)
            # Continue with other migrations even if one fails
            print(f"\n⚠️  Migration {Path(script).name} failed, continuing with others...")
    
    # Summary
    print("\n" + "="*60)
    if failed:
        print(f"⚠️  {len(failed)} code migrations failed:")
        for script in failed:
            print(f"  - {Path(script).name}")
        print("\nThe application may not work correctly.")
        print("Check the logs and fix the issues.")
        # Don't exit with error - let the app start anyway
        return 0
    else:
        print("✅ All code migrations completed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())