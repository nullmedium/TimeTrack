#!/usr/bin/env python3
"""
Fix WorkRegion enum usage throughout the codebase
"""

import os
import re
from pathlib import Path

# Define old to new region mappings
REGION_MAPPINGS = {
    'UNITED_STATES': 'USA',
    'UNITED_KINGDOM': 'UK',
    'FRANCE': 'EU',
    'EUROPEAN_UNION': 'EU', 
    'CUSTOM': 'OTHER',
}

# Note: GERMANY is kept as is - it has specific labor laws

def update_python_files():
    """Update Python files with new WorkRegion values"""
    python_files = []
    
    # Add known files
    known_files = ['app.py', 'routes/company.py', 'routes/system_admin.py']
    python_files.extend([f for f in known_files if os.path.exists(f)])
    
    # Search for more Python files
    if os.path.exists('routes'):
        python_files.extend([str(p) for p in Path('routes').glob('*.py')])
    
    # Remove duplicates
    python_files = list(set(python_files))
    
    for filepath in python_files:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Skip if no WorkRegion references
        if 'WorkRegion' not in content:
            continue
            
        print(f"Processing {filepath}...")
        
        original_content = content
        
        # Update WorkRegion enum references
        for old_region, new_region in REGION_MAPPINGS.items():
            # Update enum access: WorkRegion.OLD_REGION -> WorkRegion.NEW_REGION
            content = re.sub(
                rf'WorkRegion\.{old_region}\b',
                f'WorkRegion.{new_region}',
                content
            )
            
            # Update string comparisons
            content = re.sub(
                rf"['\"]({old_region})['\"]",
                f"'{new_region}'",
                content
            )
        
        # Add comments for GERMANY usage to note it has specific laws
        if 'WorkRegion.GERMANY' in content and '# Note:' not in content:
            content = re.sub(
                r'(WorkRegion\.GERMANY)',
                r'\1  # Germany has specific labor laws beyond EU',
                content,
                count=1  # Only comment the first occurrence
            )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def update_template_files():
    """Update template files with new WorkRegion values"""
    template_files = []
    
    # Find relevant templates
    if os.path.exists('templates'):
        for template in Path('templates').glob('*.html'):
            with open(template, 'r') as f:
                if 'region' in f.read().lower():
                    template_files.append(str(template))
    
    for filepath in template_files:
        print(f"Processing {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update region values
        for old_region, new_region in REGION_MAPPINGS.items():
            # Update in option values
            content = re.sub(
                rf'value=[\'"]{old_region}[\'"]',
                f'value="{new_region}"',
                content
            )
            
            # Update display names
            display_mappings = {
                'UNITED_STATES': 'United States',
                'United States': 'United States',
                'UNITED_KINGDOM': 'United Kingdom', 
                'United Kingdom': 'United Kingdom',
                'FRANCE': 'European Union',
                'France': 'European Union',
                'EUROPEAN_UNION': 'European Union',
                'European Union': 'European Union',
                'CUSTOM': 'Other',
                'Custom': 'Other'
            }
            
            for old_display, new_display in display_mappings.items():
                if old_display in ['France', 'FRANCE']:
                    # France is now part of EU
                    content = re.sub(
                        rf'>{old_display}<',
                        f'>{new_display}<',
                        content
                    )
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath}")
        else:
            print(f"  - No changes needed in {filepath}")

def main():
    print("=== Fixing WorkRegion Enum Usage ===\n")
    
    print("1. Updating Python files...")
    update_python_files()
    
    print("\n2. Updating template files...")
    update_template_files()
    
    print("\n✅ WorkRegion migration complete!")
    print("\nRegion mappings applied:")
    for old, new in REGION_MAPPINGS.items():
        print(f"  - {old} → {new}")
    print("\nNote: GERMANY remains as a separate option due to specific labor laws")

if __name__ == "__main__":
    main()