from app import app, db
import sqlite3
import os

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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()