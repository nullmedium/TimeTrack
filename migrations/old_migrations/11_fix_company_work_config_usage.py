#!/usr/bin/env python3
"""
Fix CompanyWorkConfig field usage throughout the codebase
"""

import os
import re
from pathlib import Path

# Define old to new field mappings
FIELD_MAPPINGS = {
    'work_hours_per_day': 'standard_hours_per_day',
    'mandatory_break_minutes': 'break_duration_minutes', 
    'break_threshold_hours': 'break_after_hours',
    'region': 'work_region',
}

# Fields that were removed
REMOVED_FIELDS = [
    'additional_break_minutes',
    'additional_break_threshold_hours', 
    'region_name',
    'created_by_id'
]

def update_python_files():
    """Update Python files with new field names"""
    python_files = [
        'app.py',
        'routes/company.py',
    ]
    
    for filepath in python_files:
        if not os.path.exists(filepath):
            print(f"Skipping {filepath} - file not found")
            continue
            
        print(f"Processing {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update field references
        for old_field, new_field in FIELD_MAPPINGS.items():
            # Update attribute access: .old_field -> .new_field
            content = re.sub(
                rf'\.{old_field}\b',
                f'.{new_field}',
                content
            )
            
            # Update dictionary access: ['old_field'] -> ['new_field']
            content = re.sub(
                rf'\[[\'"]{old_field}[\'"]\]',
                f"['{new_field}']",
                content
            )
            
            # Update keyword arguments: old_field= -> new_field=
            content = re.sub(
                rf'\b{old_field}=',
                f'{new_field}=',
                content
            )
        
        # Handle special cases for app.py
        if filepath == 'app.py':
            # Update WorkRegion.GERMANY references where appropriate
            content = re.sub(
                r'WorkRegion\.GERMANY',
                'WorkRegion.GERMANY  # Note: Germany has specific labor laws',
                content
            )
            
            # Handle removed fields - comment them out with explanation
            for removed_field in ['additional_break_minutes', 'additional_break_threshold_hours']:
                content = re.sub(
                    rf'^(\s*)(.*{removed_field}.*)$',
                    r'\1# REMOVED: \2  # This field no longer exists in the model',
                    content,
                    flags=re.MULTILINE
                )
        
        # Handle region_name specially in routes/company.py
        if filepath == 'routes/company.py':
            # Remove region_name assignments
            content = re.sub(
                r"work_config\.region_name = .*\n",
                "# region_name removed - using work_region enum value instead\n",
                content
            )
            
            # Fix WorkRegion.CUSTOM -> WorkRegion.OTHER
            content = re.sub(
                r'WorkRegion\.CUSTOM',
                'WorkRegion.OTHER',
                content
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def update_template_files():
    """Update template files with new field names"""
    template_files = [
        'templates/admin_company.html',
        'templates/admin_work_policies.html',
        'templates/config.html',
    ]
    
    for filepath in template_files:
        if not os.path.exists(filepath):
            print(f"Skipping {filepath} - file not found")
            continue
            
        print(f"Processing {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update field references in templates
        for old_field, new_field in FIELD_MAPPINGS.items():
            # Update Jinja2 variable access: {{ obj.old_field }} -> {{ obj.new_field }}
            content = re.sub(
                r'(\{\{[^}]*\.)' + re.escape(old_field) + r'(\s*\}\})',
                r'\1' + new_field + r'\2',
                content
            )
            
            # Update form field names and IDs
            content = re.sub(
                rf'(name|id)=[\'"]{old_field}[\'"]',
                rf'\1="{new_field}"',
                content
            )
        
        # Handle region_name in templates
        if 'region_name' in content:
            # Replace region_name with work_region.value
            content = re.sub(
                r'(\{\{[^}]*\.)region_name(\s*\}\})',
                r'\1work_region.value\2',
                content
            )
        
        # Handle removed fields in admin_company.html
        if filepath == 'templates/admin_company.html' and 'additional_break' in content:
            # Remove entire config-item divs for removed fields
            content = re.sub(
                r'<div class="config-item">.*?additional_break.*?</div>\s*',
                '',
                content,
                flags=re.DOTALL
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def main():
    print("=== Fixing CompanyWorkConfig Field Usage ===\n")
    
    print("1. Updating Python files...")
    update_python_files()
    
    print("\n2. Updating template files...")
    update_template_files()
    
    print("\n✅ CompanyWorkConfig migration complete!")
    print("\nNote: Some fields have been removed from the model:")
    print("  - additional_break_minutes")
    print("  - additional_break_threshold_hours")
    print("  - region_name (use work_region.value instead)")
    print("  - created_by_id")

if __name__ == "__main__":
    main()