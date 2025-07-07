#!/usr/bin/env python3
"""
Add missing columns to company_settings table
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def add_missing_columns():
    """Add missing columns to company_settings table"""
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
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'company_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                print("company_settings table does not exist. Creating it...")
                cur.execute("""
                    CREATE TABLE company_settings (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER UNIQUE NOT NULL REFERENCES company(id),
                        work_week_start INTEGER DEFAULT 1,
                        work_days VARCHAR(20) DEFAULT '1,2,3,4,5',
                        allow_overlapping_entries BOOLEAN DEFAULT FALSE,
                        require_project_for_time_entry BOOLEAN DEFAULT TRUE,
                        allow_future_entries BOOLEAN DEFAULT FALSE,
                        max_hours_per_entry FLOAT DEFAULT 24.0,
                        enable_tasks BOOLEAN DEFAULT TRUE,
                        enable_sprints BOOLEAN DEFAULT FALSE,
                        enable_client_access BOOLEAN DEFAULT FALSE,
                        notify_on_overtime BOOLEAN DEFAULT TRUE,
                        overtime_threshold_daily FLOAT DEFAULT 8.0,
                        overtime_threshold_weekly FLOAT DEFAULT 40.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Created company_settings table")
            else:
                # Check which columns exist
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'company_settings'
                """)
                existing_columns = [row[0] for row in cur.fetchall()]
                print(f"Existing columns: {existing_columns}")
                
                # Add missing columns
                columns_to_add = {
                    'work_week_start': 'INTEGER DEFAULT 1',
                    'work_days': "VARCHAR(20) DEFAULT '1,2,3,4,5'",
                    'allow_overlapping_entries': 'BOOLEAN DEFAULT FALSE',
                    'require_project_for_time_entry': 'BOOLEAN DEFAULT TRUE',
                    'allow_future_entries': 'BOOLEAN DEFAULT FALSE',
                    'max_hours_per_entry': 'FLOAT DEFAULT 24.0',
                    'enable_tasks': 'BOOLEAN DEFAULT TRUE',
                    'enable_sprints': 'BOOLEAN DEFAULT FALSE',
                    'enable_client_access': 'BOOLEAN DEFAULT FALSE',
                    'notify_on_overtime': 'BOOLEAN DEFAULT TRUE',
                    'overtime_threshold_daily': 'FLOAT DEFAULT 8.0',
                    'overtime_threshold_weekly': 'FLOAT DEFAULT 40.0',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }
                
                for column, definition in columns_to_add.items():
                    if column not in existing_columns:
                        print(f"Adding {column} column...")
                        cur.execute(f"ALTER TABLE company_settings ADD COLUMN {column} {definition}")
                        print(f"Added {column} column")
            
            # Commit changes
            conn.commit()
            print("\nCompany settings migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()