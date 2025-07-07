#!/usr/bin/env python3
"""
Add missing columns to user_dashboard table
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def add_missing_columns():
    """Add missing columns to user_dashboard table"""
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
            # Check if columns exist
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_dashboard' 
                AND column_name IN ('layout', 'is_locked', 'created_at', 'updated_at', 
                                    'name', 'is_default', 'layout_config', 'grid_columns', 
                                    'theme', 'auto_refresh')
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            
            # Add missing columns
            if 'name' not in existing_columns:
                print("Adding 'name' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN name VARCHAR(100) DEFAULT 'My Dashboard'")
                print("Added 'name' column")
                
            if 'is_default' not in existing_columns:
                print("Adding 'is_default' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN is_default BOOLEAN DEFAULT TRUE")
                print("Added 'is_default' column")
                
            if 'layout_config' not in existing_columns:
                print("Adding 'layout_config' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN layout_config TEXT")
                print("Added 'layout_config' column")
                
            if 'grid_columns' not in existing_columns:
                print("Adding 'grid_columns' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN grid_columns INTEGER DEFAULT 6")
                print("Added 'grid_columns' column")
                
            if 'theme' not in existing_columns:
                print("Adding 'theme' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN theme VARCHAR(20) DEFAULT 'light'")
                print("Added 'theme' column")
                
            if 'auto_refresh' not in existing_columns:
                print("Adding 'auto_refresh' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN auto_refresh INTEGER DEFAULT 300")
                print("Added 'auto_refresh' column")
            
            if 'layout' not in existing_columns:
                print("Adding 'layout' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN layout JSON")
                print("Added 'layout' column")
            
            if 'is_locked' not in existing_columns:
                print("Adding 'is_locked' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN is_locked BOOLEAN DEFAULT FALSE")
                print("Added 'is_locked' column")
                
            if 'created_at' not in existing_columns:
                print("Adding 'created_at' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("Added 'created_at' column")
                
            if 'updated_at' not in existing_columns:
                print("Adding 'updated_at' column to user_dashboard table...")
                cur.execute("ALTER TABLE user_dashboard ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("Added 'updated_at' column")
            
            # Commit changes
            conn.commit()
            print("Dashboard columns migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()