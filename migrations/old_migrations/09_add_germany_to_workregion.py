#!/usr/bin/env python3
"""
Add GERMANY back to work region enum
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def add_germany_to_workregion():
    """Add GERMANY to work region enum"""
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
            print("Adding GERMANY to workregion enum...")
            
            # Check if GERMANY already exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'workregion')
                    AND enumlabel = 'GERMANY'
                )
            """)
            
            if cur.fetchone()[0]:
                print("GERMANY already exists in enum")
                return
            
            # Add GERMANY to the enum after UK
            cur.execute("""
                ALTER TYPE workregion ADD VALUE IF NOT EXISTS 'GERMANY' AFTER 'UK'
            """)
            
            print("Successfully added GERMANY to enum")
            
            # Update any EU records that should be Germany based on other criteria
            # For now, we'll leave existing EU records as is, but new records can choose Germany
            
            # Verify the enum values
            print("\nCurrent workregion enum values:")
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'workregion')
                ORDER BY enumsortorder
            """)
            for row in cur.fetchall():
                print(f"  - {row[0]}")
            
            # Commit changes
            conn.commit()
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_germany_to_workregion()