#!/usr/bin/env python3
"""
Fix enum value mismatches between Python models and PostgreSQL.
The issue: Python sends enum.name ('TODO') but PostgreSQL expects enum.value ('To Do').
"""

import os
import sys

def main():
    """Fix enum mismatches."""
    print("=== Enum Value Mismatch Fix ===\n")
    
    os.environ['FLASK_APP'] = 'app.py'
    
    from app import app, db
    from models import TaskStatus, TaskPriority, Role, WorkRegion
    
    print("The Problem:")
    print("- Your Python code sends: task.status = TaskStatus.TODO")
    print("- SQLAlchemy sends to DB: 'TODO' (the enum name)")
    print("- But the enum value is: 'To Do'")
    print("- PostgreSQL expects: 'To Do' (the enum value)\n")
    
    with app.app_context():
        # Show the mismatch
        print("TaskStatus enum mapping:")
        for status in TaskStatus:
            print(f"  {status.name} -> '{status.value}'")
            print(f"    Python sends: '{status.name}'")
            print(f"    DB expects: '{status.value}'")
        
        print("\n" + "="*50)
        print("SOLUTION OPTIONS")
        print("="*50)
        
        print("\nOption 1: Add enum NAMES to PostgreSQL (Recommended)")
        print("This allows both 'TODO' and 'To Do' to work:\n")
        
        # Generate SQL to add enum names
        sql_fixes = []
        
        # Check what's in the database
        try:
            result = db.engine.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'taskstatus')
            """)
            db_values = set(row[0] for row in result)
            
            print(f"Current database values: {list(db_values)}\n")
            
            # Add missing enum NAMES
            for status in TaskStatus:
                if status.name not in db_values:
                    sql_fixes.append(f"ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS '{status.name}';")
            
            if sql_fixes:
                print("SQL to run:")
                for sql in sql_fixes:
                    print(f"  {sql}")
            
        except Exception as e:
            print(f"Error checking database: {e}")
        
        print("\n\nOption 2: Fix Python enum definitions")
        print("Change enums to use name as value:\n")
        print("# In models/enums.py:")
        print("class TaskStatus(enum.Enum):")
        print("    TODO = 'TODO'  # Instead of 'To Do'")
        print("    IN_PROGRESS = 'IN_PROGRESS'  # Instead of 'In Progress'")
        
        print("\n\nOption 3: Create migration to fix this properly")
        
        # Create a migration file
        migration_content = '''"""Fix enum value mismatches

Revision ID: fix_enum_values
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add enum NAMES as valid values (keeping the display values too)
    # This allows both 'TODO' and 'To Do' to work
    
    # TaskStatus
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'TODO';")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS';")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'IN_REVIEW';")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'DONE';")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'CANCELLED';")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED';")
    
    # TaskPriority  
    op.execute("ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'LOW';")
    op.execute("ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'MEDIUM';")
    op.execute("ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'HIGH';")
    op.execute("ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'URGENT';")
    
    # Role (if using enum in DB)
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'TEAM_MEMBER';")
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'TEAM_LEADER';")
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'SUPERVISOR';")
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'ADMIN';")
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'SYSTEM_ADMIN';")

def downgrade():
    # Cannot remove enum values in PostgreSQL
    pass
'''
        
        with open('fix_enum_values_migration.py', 'w') as f:
            f.write(migration_content)
        
        print("Created: fix_enum_values_migration.py")
        print("\nTo apply Option 1:")
        print("1. Copy the migration content to a new migration")
        print("2. Run: flask db upgrade")
        
        print("\n\nWHY THIS HAPPENS:")
        print("- SQLAlchemy sends the enum NAME (TODO) not VALUE ('To Do')")
        print("- This is a common issue with PostgreSQL enums")
        print("- Best practice: Make enum name == enum value")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())