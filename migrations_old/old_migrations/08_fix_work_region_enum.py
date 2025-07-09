#!/usr/bin/env python3
"""
Fix work region enum values in the database
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def fix_work_region_enum():
    """Update work region enum values in database"""
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
            print("Starting work region enum migration...")
            
            # First check if work_region column is using enum type
            cur.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'company_work_config' 
                AND column_name = 'work_region'
            """)
            data_type = cur.fetchone()
            
            if data_type and data_type[0] == 'USER-DEFINED':
                # It's an enum, we need to update it
                print("work_region is an enum type, migrating...")
                
                # Create temporary column
                print("1. Creating temporary column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN work_region_temp VARCHAR(50)")
                
                # Copy and map values
                print("2. Copying and mapping values...")
                cur.execute("""
                    UPDATE company_work_config SET work_region_temp = CASE
                        WHEN work_region::text = 'GERMANY' THEN 'EU'
                        WHEN work_region::text = 'DE' THEN 'EU'
                        WHEN work_region::text = 'UNITED_STATES' THEN 'USA'
                        WHEN work_region::text = 'US' THEN 'USA'
                        WHEN work_region::text = 'UNITED_KINGDOM' THEN 'UK'
                        WHEN work_region::text = 'GB' THEN 'UK'
                        WHEN work_region::text = 'FRANCE' THEN 'EU'
                        WHEN work_region::text = 'FR' THEN 'EU'
                        WHEN work_region::text = 'EUROPEAN_UNION' THEN 'EU'
                        WHEN work_region::text = 'CUSTOM' THEN 'OTHER'
                        ELSE COALESCE(work_region::text, 'OTHER')
                    END
                """)
                print(f"   Updated {cur.rowcount} rows")
                
                # Drop old column
                print("3. Dropping old work_region column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN work_region")
                
                # Check if enum type exists and drop it
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'workregion'
                    )
                """)
                if cur.fetchone()[0]:
                    print("4. Dropping old workregion enum type...")
                    cur.execute("DROP TYPE IF EXISTS workregion CASCADE")
                
                # Create new enum type
                print("5. Creating new workregion enum type...")
                cur.execute("""
                    CREATE TYPE workregion AS ENUM (
                        'USA',
                        'CANADA',
                        'UK',
                        'EU',
                        'AUSTRALIA',
                        'OTHER'
                    )
                """)
                
                # Add new column with enum type
                print("6. Adding new work_region column...")
                cur.execute("ALTER TABLE company_work_config ADD COLUMN work_region workregion DEFAULT 'OTHER'")
                
                # Copy data back
                print("7. Copying data to new column...")
                cur.execute("UPDATE company_work_config SET work_region = work_region_temp::workregion")
                
                # Drop temporary column
                print("8. Dropping temporary column...")
                cur.execute("ALTER TABLE company_work_config DROP COLUMN work_region_temp")
                
            else:
                # It's already a varchar, just update the values
                print("work_region is already a varchar, updating values...")
                cur.execute("""
                    UPDATE company_work_config SET work_region = CASE
                        WHEN work_region = 'GERMANY' THEN 'EU'
                        WHEN work_region = 'DE' THEN 'EU'
                        WHEN work_region = 'UNITED_STATES' THEN 'USA'
                        WHEN work_region = 'US' THEN 'USA'
                        WHEN work_region = 'UNITED_KINGDOM' THEN 'UK'
                        WHEN work_region = 'GB' THEN 'UK'
                        WHEN work_region = 'FRANCE' THEN 'EU'
                        WHEN work_region = 'FR' THEN 'EU'
                        WHEN work_region = 'EUROPEAN_UNION' THEN 'EU'
                        WHEN work_region = 'CUSTOM' THEN 'OTHER'
                        ELSE COALESCE(work_region, 'OTHER')
                    END
                """)
                print(f"Updated {cur.rowcount} rows")
            
            # Commit changes
            conn.commit()
            print("\nWork region enum migration completed successfully!")
            
            # Verify the results
            print("\nCurrent work_region values in database:")
            cur.execute("SELECT DISTINCT work_region FROM company_work_config ORDER BY work_region")
            for row in cur.fetchall():
                print(f"  - {row[0]}")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_work_region_enum()