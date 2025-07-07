#!/usr/bin/env python3
"""
Fix company_work_config table columns to match model definition
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def fix_company_work_config_columns():
    """Rename and add columns to match the new model definition"""
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
            # Check which columns exist
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'company_work_config'
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            print(f"Existing columns: {existing_columns}")
            
            # Rename columns if they exist with old names
            if 'work_hours_per_day' in existing_columns and 'standard_hours_per_day' not in existing_columns:
                print("Renaming work_hours_per_day to standard_hours_per_day...")
                cur.execute("ALTER TABLE company_work_config RENAME COLUMN work_hours_per_day TO standard_hours_per_day")
            
            # Add missing columns
            if 'standard_hours_per_day' not in existing_columns and 'work_hours_per_day' not in existing_columns:
                print("Adding standard_hours_per_day column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN standard_hours_per_day FLOAT DEFAULT 8.0")
            
            if 'standard_hours_per_week' not in existing_columns:
                print("Adding standard_hours_per_week column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN standard_hours_per_week FLOAT DEFAULT 40.0")
            
            # Rename region to work_region if needed
            if 'region' in existing_columns and 'work_region' not in existing_columns:
                print("Renaming region to work_region...")
                cur.execute("ALTER TABLE company_work_config RENAME COLUMN region TO work_region")
            elif 'work_region' not in existing_columns:
                print("Adding work_region column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN work_region VARCHAR(50) DEFAULT 'OTHER'")
            
            # Add new columns that don't exist
            if 'overtime_enabled' not in existing_columns:
                print("Adding overtime_enabled column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN overtime_enabled BOOLEAN DEFAULT TRUE")
            
            if 'overtime_rate' not in existing_columns:
                print("Adding overtime_rate column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN overtime_rate FLOAT DEFAULT 1.5")
            
            if 'double_time_enabled' not in existing_columns:
                print("Adding double_time_enabled column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN double_time_enabled BOOLEAN DEFAULT FALSE")
            
            if 'double_time_threshold' not in existing_columns:
                print("Adding double_time_threshold column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN double_time_threshold FLOAT DEFAULT 12.0")
            
            if 'double_time_rate' not in existing_columns:
                print("Adding double_time_rate column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN double_time_rate FLOAT DEFAULT 2.0")
            
            if 'require_breaks' not in existing_columns:
                print("Adding require_breaks column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN require_breaks BOOLEAN DEFAULT TRUE")
            
            if 'break_duration_minutes' not in existing_columns:
                # Rename mandatory_break_minutes if it exists
                if 'mandatory_break_minutes' in existing_columns:
                    print("Renaming mandatory_break_minutes to break_duration_minutes...")
                    cur.execute("ALTER TABLE company_work_config RENAME COLUMN mandatory_break_minutes TO break_duration_minutes")
                else:
                    print("Adding break_duration_minutes column...")
                    cur.execute("ALTER TABLE company_work_config ADD COLUMN break_duration_minutes INTEGER DEFAULT 30")
            
            if 'break_after_hours' not in existing_columns:
                # Rename break_threshold_hours if it exists
                if 'break_threshold_hours' in existing_columns:
                    print("Renaming break_threshold_hours to break_after_hours...")
                    cur.execute("ALTER TABLE company_work_config RENAME COLUMN break_threshold_hours TO break_after_hours")
                else:
                    print("Adding break_after_hours column...")
                    cur.execute("ALTER TABLE company_work_config ADD COLUMN break_after_hours FLOAT DEFAULT 6.0")
            
            if 'weekly_overtime_threshold' not in existing_columns:
                print("Adding weekly_overtime_threshold column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN weekly_overtime_threshold FLOAT DEFAULT 40.0")
            
            if 'weekly_overtime_rate' not in existing_columns:
                print("Adding weekly_overtime_rate column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN weekly_overtime_rate FLOAT DEFAULT 1.5")
            
            # Drop columns that are no longer needed
            if 'region_name' in existing_columns:
                print("Dropping region_name column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN region_name")
            
            if 'additional_break_minutes' in existing_columns:
                print("Dropping additional_break_minutes column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN additional_break_minutes")
            
            if 'additional_break_threshold_hours' in existing_columns:
                print("Dropping additional_break_threshold_hours column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN additional_break_threshold_hours")
            
            if 'created_by_id' in existing_columns:
                print("Dropping created_by_id column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN created_by_id")
            
            # Commit changes
            conn.commit()
            print("\nCompany work config migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_company_work_config_columns()