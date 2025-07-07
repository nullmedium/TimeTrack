#!/usr/bin/env python3
"""
Fix TaskStatus enum usage throughout the codebase
"""

import os
import re
from pathlib import Path

# Define old to new status mappings
STATUS_MAPPINGS = {
    'NOT_STARTED': 'TODO',
    'COMPLETED': 'DONE',
    'ON_HOLD': 'IN_REVIEW',
}

def update_python_files():
    """Update Python files with new TaskStatus values"""
    # Find all Python files that might use TaskStatus
    python_files = []
    
    # Add specific known files
    known_files = ['app.py', 'routes/tasks.py', 'routes/tasks_api.py', 'routes/sprints.py', 'routes/sprints_api.py']
    python_files.extend([f for f in known_files if os.path.exists(f)])
    
    # Search for more Python files in routes/
    if os.path.exists('routes'):
        python_files.extend([str(p) for p in Path('routes').glob('*.py')])
    
    # Remove duplicates
    python_files = list(set(python_files))
    
    for filepath in python_files:
        print(f"Processing {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update TaskStatus enum references
        for old_status, new_status in STATUS_MAPPINGS.items():
            # Update enum access: TaskStatus.OLD_STATUS -> TaskStatus.NEW_STATUS
            content = re.sub(
                rf'TaskStatus\.{old_status}\b',
                f'TaskStatus.{new_status}',
                content
            )
            
            # Update string comparisons: == 'OLD_STATUS' -> == 'NEW_STATUS'
            content = re.sub(
                rf"['\"]({old_status})['\"]",
                f"'{new_status}'",
                content
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def update_javascript_files():
    """Update JavaScript files with new TaskStatus values"""
    js_files = []
    
    # Find all JS files
    if os.path.exists('static/js'):
        js_files.extend([str(p) for p in Path('static/js').glob('*.js')])
    
    for filepath in js_files:
        print(f"Processing {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update status values in JavaScript
        for old_status, new_status in STATUS_MAPPINGS.items():
            # Update string literals
            content = re.sub(
                rf"['\"]({old_status})['\"]",
                f"'{new_status}'",
                content
            )
            
            # Update in case statements or object keys
            content = re.sub(
                rf'\b{old_status}\b:',
                f'{new_status}:',
                content
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def update_template_files():
    """Update template files with new TaskStatus values"""
    template_files = []
    
    # Find all template files that might have task status
    if os.path.exists('templates'):
        template_files.extend([str(p) for p in Path('templates').glob('*.html')])
    
    for filepath in template_files:
        # Skip if file doesn't contain task-related content
        with open(filepath, 'r') as f:
            content = f.read()
            
        if 'task' not in content.lower() and 'status' not in content.lower():
            continue
            
        print(f"Processing {filepath}...")
        
        original_content = content
        
        # Update status values in templates
        for old_status, new_status in STATUS_MAPPINGS.items():
            # Update in option values: value="OLD_STATUS" -> value="NEW_STATUS"
            content = re.sub(
                rf'value=[\'"]{old_status}[\'"]',
                f'value="{new_status}"',
                content
            )
            
            # Update display text (be more careful here)
            if old_status == 'NOT_STARTED':
                content = re.sub(r'>Not Started<', '>To Do<', content)
            elif old_status == 'COMPLETED':
                content = re.sub(r'>Completed<', '>Done<', content)
            elif old_status == 'ON_HOLD':
                content = re.sub(r'>On Hold<', '>In Review<', content)
            
            # Update in JavaScript within templates
            content = re.sub(
                rf"['\"]({old_status})['\"]",
                f"'{new_status}'",
                content
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def main():
    print("=== Fixing TaskStatus Enum Usage ===\n")
    
    print("1. Updating Python files...")
    update_python_files()
    
    print("\n2. Updating JavaScript files...")
    update_javascript_files()
    
    print("\n3. Updating template files...")
    update_template_files()
    
    print("\n✅ TaskStatus migration complete!")
    print("\nStatus mappings applied:")
    for old, new in STATUS_MAPPINGS.items():
        print(f"  - {old} → {new}")

if __name__ == "__main__":
    main()