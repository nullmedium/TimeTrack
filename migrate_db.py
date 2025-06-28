from app import app, db
import sqlite3
import os
from models import User, TimeEntry, WorkConfig
from werkzeug.security import generate_password_hash
from datetime import datetime

def migrate_database():
    db_path = 'timetrack.db'

    # Check if database exists
    if not os.path.exists(db_path):
        print("Database doesn't exist. Creating new database.")
        with app.app_context():
            db.create_all()
        return

    print("Migrating existing database...")

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the time_entry columns already exist
    cursor.execute("PRAGMA table_info(time_entry)")
    time_entry_columns = [column[1] for column in cursor.fetchall()]

    # Add new columns to time_entry if they don't exist
    if 'is_paused' not in time_entry_columns:
        print("Adding is_paused column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN is_paused BOOLEAN DEFAULT 0")

    if 'pause_start_time' not in time_entry_columns:
        print("Adding pause_start_time column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN pause_start_time TIMESTAMP")

    if 'total_break_duration' not in time_entry_columns:
        print("Adding total_break_duration column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN total_break_duration INTEGER DEFAULT 0")
        
    # Add user_id column if it doesn't exist
    if 'user_id' not in time_entry_columns:
        print("Adding user_id column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN user_id INTEGER")

    # Check if the work_config table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='work_config'")
    if not cursor.fetchone():
        print("Creating work_config table...")
        cursor.execute("""
        CREATE TABLE work_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_hours_per_day FLOAT DEFAULT 8.0,
            mandatory_break_minutes INTEGER DEFAULT 30,
            break_threshold_hours FLOAT DEFAULT 6.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
        """)
        # Insert default config
        cursor.execute("""
        INSERT INTO work_config (work_hours_per_day, mandatory_break_minutes, break_threshold_hours)
        VALUES (8.0, 30, 6.0)
        """)
    else:
        # Check if the work_config columns already exist
        cursor.execute("PRAGMA table_info(work_config)")
        work_config_columns = [column[1] for column in cursor.fetchall()]

        # Add new columns to work_config if they don't exist
        if 'additional_break_minutes' not in work_config_columns:
            print("Adding additional_break_minutes column to work_config...")
            cursor.execute("ALTER TABLE work_config ADD COLUMN additional_break_minutes INTEGER DEFAULT 15")

        if 'additional_break_threshold_hours' not in work_config_columns:
            print("Adding additional_break_threshold_hours column to work_config...")
            cursor.execute("ALTER TABLE work_config ADD COLUMN additional_break_threshold_hours FLOAT DEFAULT 9.0")
            
        # Add user_id column to work_config if it doesn't exist
        if 'user_id' not in work_config_columns:
            print("Adding user_id column to work_config...")
            cursor.execute("ALTER TABLE work_config ADD COLUMN user_id INTEGER")

    # Check if the user table exists and has the verification columns
    cursor.execute("PRAGMA table_info(user)")
    user_columns = [column[1] for column in cursor.fetchall()]

    # Add new columns to user table for email verification
    if 'is_verified' not in user_columns:
        print("Adding is_verified column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0")
        
    if 'verification_token' not in user_columns:
        print("Adding verification_token column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN verification_token VARCHAR(100)")
        
    if 'token_expiry' not in user_columns:
        print("Adding token_expiry column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN token_expiry TIMESTAMP")
    
    # Add is_blocked column to user table if it doesn't exist
    if 'is_blocked' not in user_columns:
        print("Adding is_blocked column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT 0")

    # Commit changes and close connection
    conn.commit()
    conn.close()

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@timetrack.local',
                is_admin=True,
                is_verified=True  # Admin is automatically verified
            )
            admin.set_password('admin')  # Default password, should be changed
            db.session.add(admin)
            db.session.commit()
            print("Created admin user with username 'admin' and password 'admin'")
            print("Please change the admin password after first login!")
        else:
            # Make sure existing admin user is verified
            if not hasattr(admin, 'is_verified') or not admin.is_verified:
                admin.is_verified = True
                db.session.commit()
                print("Marked existing admin user as verified")
        
        # Update existing time entries to associate with admin user
        orphan_entries = TimeEntry.query.filter_by(user_id=None).all()
        for entry in orphan_entries:
            entry.user_id = admin.id
        
        # Update existing work configs to associate with admin user
        orphan_configs = WorkConfig.query.filter_by(user_id=None).all()
        for config in orphan_configs:
            config.user_id = admin.id
            
        # Mark all existing users as verified for backward compatibility
        existing_users = User.query.filter_by(is_verified=None).all()
        for user in existing_users:
            user.is_verified = True
            
        db.session.commit()
        print(f"Associated {len(orphan_entries)} existing time entries with admin user")
        print(f"Associated {len(orphan_configs)} existing work configs with admin user")
        print(f"Marked {len(existing_users)} existing users as verified")

if __name__ == "__main__":
    migrate_database()
    print("Database migration completed")