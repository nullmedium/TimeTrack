#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script for TimeTrack
This script migrates data from SQLite to PostgreSQL database.
"""

import sqlite3
import psycopg2
import os
import sys
import logging
from datetime import datetime
from psycopg2.extras import RealDictCursor
import json

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SQLiteToPostgresMigration:
    def __init__(self, sqlite_path, postgres_url):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.sqlite_conn = None
        self.postgres_conn = None
        self.migration_stats = {}
        
    def connect_databases(self):
        """Connect to both SQLite and PostgreSQL databases"""
        try:
            # Connect to SQLite
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            
            # Connect to PostgreSQL
            self.postgres_conn = psycopg2.connect(self.postgres_url)
            self.postgres_conn.autocommit = False
            logger.info("Connected to PostgreSQL database")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            return False
    
    def close_connections(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.postgres_conn:
            self.postgres_conn.close()
    
    def backup_postgres(self):
        """Create a backup of existing PostgreSQL data"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Check if tables exist and have data
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                
                if tables:
                    backup_file = f"postgres_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
                    logger.info(f"Creating PostgreSQL backup: {backup_file}")
                    
                    # Use pg_dump for backup
                    os.system(f"pg_dump '{self.postgres_url}' > {backup_file}")
                    logger.info(f"Backup created: {backup_file}")
                    return backup_file
                else:
                    logger.info("No existing PostgreSQL tables found, skipping backup")
                    return None
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def check_sqlite_database(self):
        """Check if SQLite database exists and has data"""
        if not os.path.exists(self.sqlite_path):
            logger.error(f"SQLite database not found: {self.sqlite_path}")
            return False
        
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.info("SQLite database is empty, nothing to migrate")
                return False
            
            logger.info(f"Found {len(tables)} tables in SQLite database")
            return True
        except Exception as e:
            logger.error(f"Error checking SQLite database: {e}")
            return False
    
    def create_postgres_tables(self, clear_existing=False):
        """Create PostgreSQL tables using Flask-SQLAlchemy models"""
        try:
            # Import Flask app and create tables
            from app import app, db
            
            with app.app_context():
                # Set the database URI to PostgreSQL
                app.config['SQLALCHEMY_DATABASE_URI'] = self.postgres_url
                
                if clear_existing:
                    logger.info("Clearing existing PostgreSQL data...")
                    db.drop_all()
                    logger.info("Dropped all existing tables")
                
                # Create all tables
                db.create_all()
                logger.info("Created PostgreSQL tables")
                return True
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            return False
    
    def migrate_table_data(self, table_name, column_mapping=None):
        """Migrate data from SQLite table to PostgreSQL"""
        try:
            sqlite_cursor = self.sqlite_conn.cursor()
            postgres_cursor = self.postgres_conn.cursor()
            
            # Check if table exists in SQLite
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not sqlite_cursor.fetchone():
                logger.info(f"Table {table_name} does not exist in SQLite, skipping...")
                self.migration_stats[table_name] = 0
                return True
            
            # Get data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"No data found in table: {table_name}")
                self.migration_stats[table_name] = 0
                return True
            
            # Get column names
            column_names = [description[0] for description in sqlite_cursor.description]
            
            # Apply column mapping if provided
            if column_mapping:
                column_names = [column_mapping.get(col, col) for col in column_names]
            
            # Prepare insert statement
            placeholders = ', '.join(['%s'] * len(column_names))
            columns = ', '.join([f'"{col}"' for col in column_names])  # Quote column names
            insert_sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'  # Quote table name
            
            # Convert rows to list of tuples
            data_rows = []
            for row in rows:
                data_row = []
                for i, value in enumerate(row):
                    col_name = column_names[i]
                    # Handle special data type conversions
                    if value is None:
                        data_row.append(None)
                    elif isinstance(value, str) and value.startswith('{"') and value.endswith('}'):
                        # Handle JSON strings
                        data_row.append(value)
                    elif (col_name.startswith('is_') or col_name.endswith('_enabled') or col_name in ['is_paused']) and isinstance(value, int):
                        # Convert integer boolean to actual boolean for PostgreSQL
                        data_row.append(bool(value))
                    elif isinstance(value, str) and value == '':
                        # Convert empty strings to None for PostgreSQL
                        data_row.append(None)
                    else:
                        data_row.append(value)
                data_rows.append(tuple(data_row))
            
            # Check if we should clear existing data first (for tables with unique constraints)
            if table_name in ['company', 'team', 'user']:
                postgres_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                existing_count = postgres_cursor.fetchone()[0]
                if existing_count > 0:
                    logger.warning(f"Table {table_name} already has {existing_count} rows. Skipping to avoid duplicates.")
                    self.migration_stats[table_name] = 0
                    return True
            
            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data_rows), batch_size):
                batch = data_rows[i:i + batch_size]
                try:
                    postgres_cursor.executemany(insert_sql, batch)
                    self.postgres_conn.commit()
                except Exception as batch_error:
                    logger.error(f"Error inserting batch {i//batch_size + 1} for table {table_name}: {batch_error}")
                    # Try inserting rows one by one to identify problematic rows
                    self.postgres_conn.rollback()
                    for j, row in enumerate(batch):
                        try:
                            postgres_cursor.execute(insert_sql, row)
                            self.postgres_conn.commit()
                        except Exception as row_error:
                            logger.error(f"Error inserting row {i + j} in table {table_name}: {row_error}")
                            logger.error(f"Problematic row data: {row}")
                            self.postgres_conn.rollback()
            
            logger.info(f"Migrated {len(rows)} rows from table: {table_name}")
            self.migration_stats[table_name] = len(rows)
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            self.postgres_conn.rollback()
            return False
    
    def update_sequences(self):
        """Update PostgreSQL sequences after data migration"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Get all sequences - fix the query to properly extract sequence names
                cursor.execute("""
                    SELECT 
                        pg_get_serial_sequence(table_name, column_name) as sequence_name,
                        column_name, 
                        table_name 
                    FROM information_schema.columns 
                    WHERE column_default LIKE 'nextval%'
                    AND table_schema = 'public'
                """)
                sequences = cursor.fetchall()
                
                for seq_name, col_name, table_name in sequences:
                    if seq_name is None:
                        continue
                    # Get the maximum value for each sequence
                    cursor.execute(f'SELECT MAX("{col_name}") FROM "{table_name}"')
                    max_val = cursor.fetchone()[0]
                    
                    if max_val is not None:
                        # Update sequence to start from max_val + 1 - don't quote sequence name from pg_get_serial_sequence
                        cursor.execute(f'ALTER SEQUENCE {seq_name} RESTART WITH {max_val + 1}')
                        logger.info(f"Updated sequence {seq_name} to start from {max_val + 1}")
                
                self.postgres_conn.commit()
                logger.info("Updated PostgreSQL sequences")
                return True
        except Exception as e:
            logger.error(f"Failed to update sequences: {e}")
            self.postgres_conn.rollback()
            return False
    
    def migrate_all_data(self):
        """Migrate all data from SQLite to PostgreSQL"""
        # Define table migration order (respecting foreign key constraints)
        migration_order = [
            'company',
            'team',
            'project_category',
            'user',
            'project',
            'task',
            'sub_task',
            'time_entry',
            'work_config',
            'company_work_config',
            'user_preferences',
            'system_settings'
        ]
        
        for table_name in migration_order:
            if not self.migrate_table_data(table_name):
                logger.error(f"Migration failed at table: {table_name}")
                return False
        
        # Update sequences after all data is migrated
        if not self.update_sequences():
            logger.error("Failed to update sequences")
            return False
        
        return True
    
    def verify_migration(self):
        """Verify that migration was successful"""
        try:
            sqlite_cursor = self.sqlite_conn.cursor()
            postgres_cursor = self.postgres_conn.cursor()
            
            # Get table names from SQLite
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            sqlite_tables = [row[0] for row in sqlite_cursor.fetchall()]
            
            verification_results = {}
            
            for table_name in sqlite_tables:
                if table_name == 'sqlite_sequence':
                    continue
                    
                # Count rows in SQLite
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Count rows in PostgreSQL
                postgres_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                postgres_count = postgres_cursor.fetchone()[0]
                
                verification_results[table_name] = {
                    'sqlite_count': sqlite_count,
                    'postgres_count': postgres_count,
                    'match': sqlite_count == postgres_count
                }
                
                if sqlite_count == postgres_count:
                    logger.info(f"✓ Table {table_name}: {sqlite_count} rows migrated successfully")
                else:
                    logger.error(f"✗ Table {table_name}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return None
    
    def run_migration(self, clear_existing=False):
        """Run the complete migration process"""
        logger.info("Starting SQLite to PostgreSQL migration...")
        
        # Connect to databases
        if not self.connect_databases():
            return False
        
        try:
            # Check SQLite database
            if not self.check_sqlite_database():
                return False
            
            # Create backup
            backup_file = self.backup_postgres()
            
            # Create PostgreSQL tables
            if not self.create_postgres_tables(clear_existing=clear_existing):
                return False
            
            # Migrate data
            if not self.migrate_all_data():
                return False
            
            # Verify migration
            verification = self.verify_migration()
            if verification:
                logger.info("Migration verification completed")
                for table, stats in verification.items():
                    if not stats['match']:
                        logger.error(f"Migration verification failed for table: {table}")
                        return False
            
            logger.info("Migration completed successfully!")
            logger.info(f"Migration statistics: {self.migration_stats}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            self.close_connections()

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate SQLite to PostgreSQL')
    parser.add_argument('--clear-existing', action='store_true', 
                       help='Clear existing PostgreSQL data before migration')
    parser.add_argument('--sqlite-path', default=os.environ.get('SQLITE_PATH', '/data/timetrack.db'),
                       help='Path to SQLite database')
    args = parser.parse_args()
    
    # Get database paths from environment variables
    sqlite_path = args.sqlite_path
    postgres_url = os.environ.get('DATABASE_URL')
    
    if not postgres_url:
        logger.error("DATABASE_URL environment variable not set")
        return 1
    
    # Check if SQLite database exists
    if not os.path.exists(sqlite_path):
        logger.info(f"SQLite database not found at {sqlite_path}, skipping migration")
        return 0
    
    # Run migration
    migration = SQLiteToPostgresMigration(sqlite_path, postgres_url)
    success = migration.run_migration(clear_existing=args.clear_existing)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())