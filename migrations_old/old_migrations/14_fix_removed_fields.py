#!/usr/bin/env python3
"""
Fix references to removed fields throughout the codebase
"""

import os
import re
from pathlib import Path

# Fields that were removed from various models
REMOVED_FIELDS = {
    'created_by_id': {
        'models': ['Task', 'Project', 'Sprint', 'Announcement', 'CompanyWorkConfig'],
        'replacement': 'None',  # or could track via audit log
        'comment': 'Field removed - consider using audit log for creator tracking'
    },
    'region_name': {
        'models': ['CompanyWorkConfig'],
        'replacement': 'work_region.value',
        'comment': 'Use work_region enum value instead'
    },
    'additional_break_minutes': {
        'models': ['CompanyWorkConfig'],
        'replacement': 'None',
        'comment': 'Field removed - simplified break configuration'
    },
    'additional_break_threshold_hours': {
        'models': ['CompanyWorkConfig'],
        'replacement': 'None',
        'comment': 'Field removed - simplified break configuration'
    }
}

def update_python_files():
    """Update Python files to handle removed fields"""
    python_files = []
    
    # Get all Python files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and cache
        if 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    for filepath in python_files:
        # Skip migration scripts
        if 'migrations/' in filepath:
            continue
            
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        for field, info in REMOVED_FIELDS.items():
            if field not in content:
                continue
                
            print(f"Processing {filepath} for {field}...")
            
            # Handle different patterns
            if field == 'created_by_id':
                # Comment out lines that assign created_by_id
                content = re.sub(
                    rf'^(\s*)([^#\n]*created_by_id\s*=\s*[^,\n]+,?)(.*)$',
                    rf'\1# REMOVED: \2  # {info["comment"]}\3',
                    content,
                    flags=re.MULTILINE
                )
                
                # Remove from query filters
                content = re.sub(
                    rf'\.filter_by\(created_by_id=[^)]+\)',
                    '.filter_by()  # REMOVED: created_by_id filter',
                    content
                )
                
                # Remove from dictionary accesses
                content = re.sub(
                    rf"['\"]created_by_id['\"]\s*:\s*[^,}}]+[,}}]",
                    '# "created_by_id" removed from model',
                    content
                )
                
            elif field == 'region_name':
                # Replace with work_region.value
                content = re.sub(
                    rf'\.region_name\b',
                    '.work_region.value',
                    content
                )
                content = re.sub(
                    rf"\['region_name'\]",
                    "['work_region'].value",
                    content
                )
                
            elif field in ['additional_break_minutes', 'additional_break_threshold_hours']:
                # Comment out references
                content = re.sub(
                    rf'^(\s*)([^#\n]*{field}[^#\n]*)$',
                    rf'\1# REMOVED: \2  # {info["comment"]}',
                    content,
                    flags=re.MULTILINE
                )
            
            if content != original_content:
                modified = True
        
        if modified:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")

def update_template_files():
    """Update template files to handle removed fields"""
    template_files = []
    
    if os.path.exists('templates'):
        template_files = [str(p) for p in Path('templates').glob('*.html')]
    
    for filepath in template_files:
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        for field, info in REMOVED_FIELDS.items():
            if field not in content:
                continue
                
            print(f"Processing {filepath} for {field}...")
            
            if field == 'created_by_id':
                # Remove or comment out created_by references in templates
                # Match {{...created_by_id...}} patterns
                pattern = r'\{\{[^}]*\.created_by_id[^}]*\}\}'
                content = re.sub(
                    pattern,
                    '<!-- REMOVED: created_by_id no longer available -->',
                    content
                )
                
            elif field == 'region_name':
                # Replace with work_region.value
                # Match {{...region_name...}} and replace region_name with work_region.value
                pattern = r'(\{\{[^}]*\.)region_name([^}]*\}\})'
                content = re.sub(
                    pattern,
                    r'\1work_region.value\2',
                    content
                )
                
            elif field in ['additional_break_minutes', 'additional_break_threshold_hours']:
                # Remove entire form groups for these fields
                pattern = r'<div[^>]*>(?:[^<]|<(?!/div))*' + re.escape(field) + r'.*?</div>\s*'
                content = re.sub(
                    pattern,
                    f'<!-- REMOVED: {field} no longer in model -->\n',
                    content,
                    flags=re.DOTALL
                )
            
            if content != original_content:
                modified = True
        
        if modified:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")

def create_audit_log_migration():
    """Create a migration to add audit fields if needed"""
    migration_content = '''#!/usr/bin/env python3
"""
Add audit log fields to replace removed created_by_id
"""

# This is a template for adding audit logging if needed
# to replace the removed created_by_id functionality

def add_audit_fields():
    """
    Consider adding these fields to models that lost created_by_id:
    - created_by_username (store username instead of ID)
    - created_at (if not already present)
    - updated_by_username
    - updated_at
    
    Or implement a separate audit log table
    """
    pass

if __name__ == "__main__":
    print("Consider implementing audit logging to track who created/modified records")
'''
    
    with open('migrations/05_add_audit_fields_template.py', 'w') as f:
        f.write(migration_content)
    print("\n✓ Created template for audit field migration")

def main():
    print("=== Fixing References to Removed Fields ===\n")
    
    print("1. Updating Python files...")
    update_python_files()
    
    print("\n2. Updating template files...")
    update_template_files()
    
    print("\n3. Creating audit field migration template...")
    create_audit_log_migration()
    
    print("\n✅ Removed fields migration complete!")
    print("\nFields handled:")
    for field, info in REMOVED_FIELDS.items():
        print(f"  - {field}: {info['comment']}")
    
    print("\n⚠️  Important: Review commented-out code and decide on appropriate replacements")
    print("   Consider implementing audit logging for creator tracking")

if __name__ == "__main__":
    main()