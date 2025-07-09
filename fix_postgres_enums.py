#!/usr/bin/env python3
"""
Fix PostgreSQL enum issues for Flask-Migrate.
Handles the TODO vs To Do issue and other enum mismatches.
"""

import os
import sys

def main():
    """Fix enum issues."""
    print("=== PostgreSQL Enum Fix ===\n")
    
    os.environ['FLASK_APP'] = 'app.py'
    
    from app import app, db
    from models import TaskStatus, TaskPriority, Role, WorkRegion
    
    with app.app_context():
        print("Checking enum values in database vs models...\n")
        
        # Check all enums
        enums_to_check = [
            ('taskstatus', TaskStatus, 'task', 'status'),
            ('taskpriority', TaskPriority, 'task', 'priority'),
            ('role', Role, 'user', 'role'),
            ('workregion', WorkRegion, 'company_work_config', 'work_region')
        ]
        
        fixes_needed = []
        
        for enum_name, enum_class, table_name, column_name in enums_to_check:
            print(f"Checking {enum_name}:")
            
            try:
                # Get database values
                result = db.engine.execute(f"""
                    SELECT enumlabel 
                    FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '{enum_name}')
                    ORDER BY enumsortorder
                """)
                db_values = [row[0] for row in result]
                print(f"  Database values: {db_values}")
                
                # Get model values - use the actual enum values, not names
                model_values = [item.value for item in enum_class]
                print(f"  Model values: {model_values}")
                
                # Debug: also show enum names vs values
                print(f"  Model enum mapping:")
                for item in enum_class:
                    print(f"    {item.name} = '{item.value}'")
                
                # Check for mismatches
                missing_in_db = set(model_values) - set(db_values)
                extra_in_db = set(db_values) - set(model_values)
                
                if missing_in_db:
                    print(f"  ⚠️  Missing in database: {missing_in_db}")
                    for value in missing_in_db:
                        fixes_needed.append(f"ALTER TYPE {enum_name} ADD VALUE '{value}';")
                
                if extra_in_db:
                    print(f"  ⚠️  Extra in database (not in model): {extra_in_db}")
                    # Note: Can't easily remove enum values in PostgreSQL
                
                if not missing_in_db and not extra_in_db:
                    print("  ✅ All values match")
                    
            except Exception as e:
                print(f"  ❌ Error checking {enum_name}: {e}")
            
            print()
        
        if fixes_needed:
            print("\nRequired fixes:")
            print("Create a new migration and add these to the upgrade() function:\n")
            
            for fix in fixes_needed:
                print(f"    op.execute(\"{fix}\")")
            
            print("\nOr run this SQL directly:")
            for fix in fixes_needed:
                print(fix)
                
            # Create a migration file
            print("\n\nCreating migration file...")
            migration_content = '''"""Fix enum values

Revision ID: fix_enums
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Fix enum values
'''
            for fix in fixes_needed:
                migration_content += f'    op.execute("{fix}")\n'
            
            migration_content += '''
def downgrade():
    # Note: PostgreSQL doesn't support removing enum values
    pass
'''
            
            with open('fix_enums_migration.py', 'w') as f:
                f.write(migration_content)
            
            print("✅ Created fix_enums_migration.py")
            print("\nTo apply, either:")
            print("1. Copy this content to a new migration file")
            print("2. Run the SQL commands directly")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())