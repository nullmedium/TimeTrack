#!/usr/bin/env python3
"""
Add missing columns to user_preferences table
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://timetrack:timetrack123@localhost:5432/timetrack')

def add_missing_columns():
    """Add missing columns to user_preferences table"""
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
                    WHERE table_name = 'user_preferences'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                print("user_preferences table does not exist. Creating it...")
                cur.execute("""
                    CREATE TABLE user_preferences (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER UNIQUE NOT NULL REFERENCES "user"(id),
                        theme VARCHAR(20) DEFAULT 'light',
                        language VARCHAR(10) DEFAULT 'en',
                        timezone VARCHAR(50) DEFAULT 'UTC',
                        date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD',
                        time_format VARCHAR(10) DEFAULT '24h',
                        email_notifications BOOLEAN DEFAULT TRUE,
                        email_daily_summary BOOLEAN DEFAULT FALSE,
                        email_weekly_summary BOOLEAN DEFAULT TRUE,
                        default_project_id INTEGER REFERENCES project(id),
                        timer_reminder_enabled BOOLEAN DEFAULT TRUE,
                        timer_reminder_interval INTEGER DEFAULT 60,
                        dashboard_layout JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Created user_preferences table")
            else:
                # Check which columns exist
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_preferences' 
                    AND column_name IN ('theme', 'language', 'timezone', 'date_format', 
                                        'time_format', 'email_notifications', 'email_daily_summary',
                                        'email_weekly_summary', 'default_project_id', 
                                        'timer_reminder_enabled', 'timer_reminder_interval',
                                        'dashboard_layout', 'created_at', 'updated_at')
                """)
                existing_columns = [row[0] for row in cur.fetchall()]
                
                # Add missing columns
                if 'theme' not in existing_columns:
                    print("Adding 'theme' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN theme VARCHAR(20) DEFAULT 'light'")
                    print("Added 'theme' column")
                    
                if 'language' not in existing_columns:
                    print("Adding 'language' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN language VARCHAR(10) DEFAULT 'en'")
                    print("Added 'language' column")
                    
                if 'timezone' not in existing_columns:
                    print("Adding 'timezone' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC'")
                    print("Added 'timezone' column")
                    
                if 'date_format' not in existing_columns:
                    print("Adding 'date_format' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD'")
                    print("Added 'date_format' column")
                    
                if 'time_format' not in existing_columns:
                    print("Adding 'time_format' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN time_format VARCHAR(10) DEFAULT '24h'")
                    print("Added 'time_format' column")
                    
                if 'email_notifications' not in existing_columns:
                    print("Adding 'email_notifications' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE")
                    print("Added 'email_notifications' column")
                    
                if 'email_daily_summary' not in existing_columns:
                    print("Adding 'email_daily_summary' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN email_daily_summary BOOLEAN DEFAULT FALSE")
                    print("Added 'email_daily_summary' column")
                    
                if 'email_weekly_summary' not in existing_columns:
                    print("Adding 'email_weekly_summary' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN email_weekly_summary BOOLEAN DEFAULT TRUE")
                    print("Added 'email_weekly_summary' column")
                    
                if 'default_project_id' not in existing_columns:
                    print("Adding 'default_project_id' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN default_project_id INTEGER REFERENCES project(id)")
                    print("Added 'default_project_id' column")
                    
                if 'timer_reminder_enabled' not in existing_columns:
                    print("Adding 'timer_reminder_enabled' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN timer_reminder_enabled BOOLEAN DEFAULT TRUE")
                    print("Added 'timer_reminder_enabled' column")
                    
                if 'timer_reminder_interval' not in existing_columns:
                    print("Adding 'timer_reminder_interval' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN timer_reminder_interval INTEGER DEFAULT 60")
                    print("Added 'timer_reminder_interval' column")
                    
                if 'dashboard_layout' not in existing_columns:
                    print("Adding 'dashboard_layout' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN dashboard_layout JSON")
                    print("Added 'dashboard_layout' column")
                    
                if 'created_at' not in existing_columns:
                    print("Adding 'created_at' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    print("Added 'created_at' column")
                    
                if 'updated_at' not in existing_columns:
                    print("Adding 'updated_at' column to user_preferences table...")
                    cur.execute("ALTER TABLE user_preferences ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    print("Added 'updated_at' column")
            
            # Commit changes
            conn.commit()
            print("User preferences migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()