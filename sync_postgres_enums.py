#!/usr/bin/env python3
"""
Automatically sync PostgreSQL enums with Python models.
Run this before starting the application to ensure all enum values exist.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

def get_enum_values_from_db(engine, enum_name):
    """Get current enum values from PostgreSQL."""
    try:
        result = engine.execute(text(f"""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = :enum_name)
            ORDER BY enumsortorder
        """), {"enum_name": enum_name})
        return set(row[0] for row in result)
    except Exception:
        return set()

def sync_enum(engine, enum_name, python_enum_class):
    """Sync a PostgreSQL enum with Python enum values."""
    print(f"\nSyncing {enum_name}...")
    
    # Get current DB values
    db_values = get_enum_values_from_db(engine, enum_name)
    if not db_values:
        print(f"  ⚠️  Enum {enum_name} not found in database (might not be used)")
        return
    
    print(f"  DB values: {sorted(db_values)}")
    
    # Get Python values - BOTH name and value
    python_values = set()
    for item in python_enum_class:
        python_values.add(item.name)   # Add the NAME (what SQLAlchemy sends)
        python_values.add(item.value)  # Add the VALUE (for compatibility)
    
    print(f"  Python values: {sorted(python_values)}")
    
    # Find missing values
    missing_values = python_values - db_values
    
    if not missing_values:
        print(f"  ✅ All values present")
        return
    
    # Add missing values
    print(f"  📝 Adding missing values: {missing_values}")
    for value in missing_values:
        try:
            # Use parameterized query for safety, but we need dynamic SQL for ALTER TYPE
            # Validate that value is safe (alphanumeric, spaces, underscores only)
            if not all(c.isalnum() or c in ' _-' for c in value):
                print(f"  ⚠️  Skipping unsafe value: {value}")
                continue
                
            engine.execute(text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"))
            print(f"  ✅ Added: {value}")
        except Exception as e:
            print(f"  ❌ Failed to add {value}: {e}")

def main():
    """Main sync function."""
    print("=== PostgreSQL Enum Sync ===")
    
    # Get database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return 1
    
    # Create engine
    engine = create_engine(database_url)
    
    # Import enums
    try:
        from models.enums import TaskStatus, TaskPriority, Role, WorkRegion, SprintStatus
        
        # Define enum mappings (db_type_name, python_enum_class)
        enum_mappings = [
            ('taskstatus', TaskStatus),
            ('taskpriority', TaskPriority),
            ('role', Role),
            ('workregion', WorkRegion),
            ('sprintstatus', SprintStatus),
        ]
        
        # Sync each enum
        for db_enum_name, python_enum in enum_mappings:
            sync_enum(engine, db_enum_name, python_enum)
        
        print("\n✅ Enum sync complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        engine.dispose()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())