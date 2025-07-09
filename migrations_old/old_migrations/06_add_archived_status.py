#!/usr/bin/env python3
"""
Add ARCHIVED status back to task status enum
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def add_archived_status():
    """Add ARCHIVED status to task status enum"""
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
            print("Adding ARCHIVED status to taskstatus enum...")
            
            # Check if ARCHIVED already exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'taskstatus')
                    AND enumlabel = 'ARCHIVED'
                )
            """)
            
            if cur.fetchone()[0]:
                print("ARCHIVED status already exists in enum")
                return
            
            # Add ARCHIVED to the enum
            cur.execute("""
                ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED' AFTER 'CANCELLED'
            """)
            
            print("Successfully added ARCHIVED status to enum")
            
            # Verify the enum values
            print("\nCurrent taskstatus enum values:")
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
    add_archived_status()