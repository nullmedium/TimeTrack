#!/usr/bin/env python3
"""
Fix task status enum in the database to match Python enum
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def fix_task_status_enum():
    """Update task status enum in database"""
    # Parse database URL
    parsed = urlparse(DATABASE_URL)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:]  # Remove leading slash
    )
    
    try:
        with conn.cursor() as cur:
            print("Starting task status enum migration...")
            
            # First check if the enum already has the correct values
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'taskstatus')
                ORDER BY enumsortorder
            """)
            current_values = [row[0] for row in cur.fetchall()]
            print(f"Current enum values: {current_values}")
            
            # Check if migration is needed
            expected_values = ['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE', 'CANCELLED']
            if all(val in current_values for val in expected_values):
                print("Task status enum already has correct values. Skipping migration.")
                return
            
            # Check if task table exists and has a status column
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'task' AND column_name = 'status'
            """)
            if not cur.fetchone():
                print("No task table or status column found. Skipping migration.")
                return
            
            # Check if temporary column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'task' AND column_name = 'status_temp'
            """)
            temp_exists = cur.fetchone() is not None
            
            if not temp_exists:
                # First, we need to create a temporary column to hold the data
                print("1. Creating temporary column...")
                cur.execute("ALTER TABLE task ADD COLUMN status_temp VARCHAR(50)")
                cur.execute("ALTER TABLE sub_task ADD COLUMN status_temp VARCHAR(50)")
            else:
                print("1. Temporary column already exists...")
            
            # Copy current status values to temp column with mapping
            print("2. Copying and mapping status values...")
            # First check what values actually exist in the database
            cur.execute("SELECT DISTINCT status::text FROM task WHERE status IS NOT NULL")
            existing_statuses = [row[0] for row in cur.fetchall()]
            print(f"   Existing status values in task table: {existing_statuses}")
            
            # If no statuses exist, skip the mapping
            if not existing_statuses:
                print("   No existing status values to migrate")
            else:
                # Build dynamic mapping based on what exists
                mapping_sql = "UPDATE task SET status_temp = CASE "
                has_cases = False
                if 'NOT_STARTED' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'NOT_STARTED' THEN 'TODO' "
                    has_cases = True
                if 'TODO' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'TODO' THEN 'TODO' "
                    has_cases = True
                if 'IN_PROGRESS' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'IN_PROGRESS' THEN 'IN_PROGRESS' "
                    has_cases = True
                if 'ON_HOLD' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'ON_HOLD' THEN 'IN_REVIEW' "
                    has_cases = True
                if 'IN_REVIEW' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'IN_REVIEW' THEN 'IN_REVIEW' "
                    has_cases = True
                if 'COMPLETED' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'COMPLETED' THEN 'DONE' "
                    has_cases = True
                if 'DONE' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'DONE' THEN 'DONE' "
                    has_cases = True
                if 'CANCELLED' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'CANCELLED' THEN 'CANCELLED' "
                    has_cases = True
                if 'ARCHIVED' in existing_statuses:
                    mapping_sql += "WHEN status::text = 'ARCHIVED' THEN 'CANCELLED' "
                    has_cases = True
                    
                if has_cases:
                    mapping_sql += "ELSE status::text END WHERE status IS NOT NULL"
                    cur.execute(mapping_sql)
            print(f"   Updated {cur.rowcount} tasks")
            
            # Check sub_task table
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sub_task' AND column_name = 'status'
            """)
            if cur.fetchone():
                # Get existing subtask statuses
                cur.execute("SELECT DISTINCT status::text FROM sub_task WHERE status IS NOT NULL")
                existing_subtask_statuses = [row[0] for row in cur.fetchall()]
                print(f"   Existing status values in sub_task table: {existing_subtask_statuses}")
                
                # If no statuses exist, skip the mapping
                if not existing_subtask_statuses:
                    print("   No existing subtask status values to migrate")
                else:
                    # Build dynamic mapping for subtasks
                    mapping_sql = "UPDATE sub_task SET status_temp = CASE "
                    has_cases = False
                    if 'NOT_STARTED' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'NOT_STARTED' THEN 'TODO' "
                        has_cases = True
                    if 'TODO' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'TODO' THEN 'TODO' "
                        has_cases = True
                    if 'IN_PROGRESS' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'IN_PROGRESS' THEN 'IN_PROGRESS' "
                        has_cases = True
                    if 'ON_HOLD' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'ON_HOLD' THEN 'IN_REVIEW' "
                        has_cases = True
                    if 'IN_REVIEW' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'IN_REVIEW' THEN 'IN_REVIEW' "
                        has_cases = True
                    if 'COMPLETED' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'COMPLETED' THEN 'DONE' "
                        has_cases = True
                    if 'DONE' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'DONE' THEN 'DONE' "
                        has_cases = True
                    if 'CANCELLED' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'CANCELLED' THEN 'CANCELLED' "
                        has_cases = True
                    if 'ARCHIVED' in existing_subtask_statuses:
                        mapping_sql += "WHEN status::text = 'ARCHIVED' THEN 'CANCELLED' "
                        has_cases = True
                        
                    if has_cases:
                        mapping_sql += "ELSE status::text END WHERE status IS NOT NULL"
                        cur.execute(mapping_sql)
            print(f"   Updated {cur.rowcount} subtasks")
            
            # Drop the old status columns
            print("3. Dropping old status columns...")
            cur.execute("ALTER TABLE task DROP COLUMN status")
            cur.execute("ALTER TABLE sub_task DROP COLUMN status")
            
            # Drop the old enum type
            print("4. Dropping old enum type...")
            cur.execute("DROP TYPE IF EXISTS taskstatus")
            
            # Create new enum type with correct values
            print("5. Creating new enum type...")
            cur.execute("""
                CREATE TYPE taskstatus AS ENUM (
                    'TODO',
                    'IN_PROGRESS',
                    'IN_REVIEW',
                    'DONE',
                    'CANCELLED'
                )
            """)
            
            # Add new status columns with correct enum type
            print("6. Adding new status columns...")
            cur.execute("ALTER TABLE task ADD COLUMN status taskstatus")
            cur.execute("ALTER TABLE sub_task ADD COLUMN status taskstatus")
            
            # Copy data from temp columns to new status columns
            print("7. Copying data to new columns...")
            cur.execute("UPDATE task SET status = status_temp::taskstatus")
            cur.execute("UPDATE sub_task SET status = status_temp::taskstatus")
            
            # Drop temporary columns
            print("8. Dropping temporary columns...")
            cur.execute("ALTER TABLE task DROP COLUMN status_temp")
            cur.execute("ALTER TABLE sub_task DROP COLUMN status_temp")
            
            # Add NOT NULL constraint
            print("9. Adding NOT NULL constraints...")
            cur.execute("ALTER TABLE task ALTER COLUMN status SET NOT NULL")
            cur.execute("ALTER TABLE sub_task ALTER COLUMN status SET NOT NULL")
            
            # Set default value
            print("10. Setting default values...")
            cur.execute("ALTER TABLE task ALTER COLUMN status SET DEFAULT 'TODO'")
            cur.execute("ALTER TABLE sub_task ALTER COLUMN status SET DEFAULT 'TODO'")
            
            # Commit changes
            conn.commit()
            print("\nTask status enum migration completed successfully!")
            
            # Verify the new enum values
            print("\nVerifying new enum values:")
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'taskstatus'
                )
                ORDER BY enumsortorder
            """)
            for row in cur.fetchall():
                print(f"  - {row[0]}")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_task_status_enum()