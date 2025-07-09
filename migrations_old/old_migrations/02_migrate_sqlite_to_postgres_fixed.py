#!/usr/bin/env python3
"""
Fixed SQLite to PostgreSQL Migration Script for TimeTrack
This script properly handles empty SQLite databases and column mapping issues.
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
        
        # Column mapping for SQLite to PostgreSQL
        self.column_mapping = {
            'project': {
                # Map SQLite columns to PostgreSQL columns
                # Ensure company_id is properly mapped
                'company_id': 'company_id',
                'user_id': 'company_id'  # Map user_id to company_id if needed
            }
        }
        
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
            for table in tables:
                logger.info(f"  - {table[0]}")
            return True
        except Exception as e:
            logger.error(f"Error checking SQLite database: {e}")
            return False
    
    def clear_postgres_data(self):
        """Clear existing data from PostgreSQL tables that will be migrated"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Tables to clear in reverse order of dependencies
                tables_to_clear = [
                    'time_entry',
                    'sub_task',
                    'task',
                    'project',
                    'user',
                    'team',
                    'company',
                    'work_config',
                    'system_settings'
                ]
                
                for table in tables_to_clear:
                    try:
                        cursor.execute(f'DELETE FROM "{table}"')
                        logger.info(f"Cleared table: {table}")
                    except Exception as e:
                        logger.warning(f"Could not clear table {table}: {e}")
                        self.postgres_conn.rollback()
                
                self.postgres_conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to clear PostgreSQL data: {e}")
            self.postgres_conn.rollback()
            return False
    
    def migrate_table_data(self, table_name):
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
            
            # Get column names from SQLite
            column_names = [description[0] for description in sqlite_cursor.description]
            logger.info(f"SQLite columns for {table_name}: {column_names}")
            
            # Get PostgreSQL column names
            postgres_cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table_name,))
            pg_columns = [row[0] for row in postgres_cursor.fetchall()]
            logger.info(f"PostgreSQL columns for {table_name}: {pg_columns}")
            
            # For project table, ensure company_id is properly handled
            if table_name == 'project':
                # Check if company_id exists in the data
                for i, row in enumerate(rows):
                    row_dict = dict(zip(column_names, row))
                    if 'company_id' not in row_dict or row_dict['company_id'] is None:
                        # If user_id exists, use it as company_id
                        if 'user_id' in row_dict and row_dict['user_id'] is not None:
                            logger.info(f"Mapping user_id {row_dict['user_id']} to company_id for project {row_dict.get('id')}")
                            # Update the row data
                            row_list = list(row)
                            if 'company_id' in column_names:
                                company_id_idx = column_names.index('company_id')
                                user_id_idx = column_names.index('user_id')
                                row_list[company_id_idx] = row_list[user_id_idx]
                            else:
                                # Add company_id column
                                column_names.append('company_id')
                                user_id_idx = column_names.index('user_id')
                                row_list.append(row[user_id_idx])
                            rows[i] = tuple(row_list)
            
            # Filter columns to only those that exist in PostgreSQL
            valid_columns = [col for col in column_names if col in pg_columns]
            column_indices = [column_names.index(col) for col in valid_columns]
            
            # Prepare insert statement
            placeholders = ', '.join(['%s'] * len(valid_columns))
            columns = ', '.join([f'"{col}"' for col in valid_columns])
            insert_sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'
            
            # Convert rows to list of tuples with only valid columns
            data_rows = []
            for row in rows:
                data_row = []
                for i in column_indices:
                    value = row[i]
                    col_name = valid_columns[column_indices.index(i)]
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
            
            # Insert data one by one to better handle errors
            successful_inserts = 0
            for i, row in enumerate(data_rows):
                try:
                    postgres_cursor.execute(insert_sql, row)
                    self.postgres_conn.commit()
                    successful_inserts += 1
                except Exception as row_error:
                    logger.error(f"Error inserting row {i} in table {table_name}: {row_error}")
                    logger.error(f"Problematic row data: {row}")
                    logger.error(f"Columns: {valid_columns}")
                    self.postgres_conn.rollback()
            
            logger.info(f"Migrated {successful_inserts}/{len(rows)} rows from table: {table_name}")
            self.migration_stats[table_name] = successful_inserts
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            self.postgres_conn.rollback()
            return False
    
    def update_sequences(self):
        """Update PostgreSQL sequences after data migration"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Get all sequences
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
                        # Update sequence to start from max_val + 1
                        cursor.execute(f'ALTER SEQUENCE {seq_name} RESTART WITH {max_val + 1}')
                        logger.info(f"Updated sequence {seq_name} to start from {max_val + 1}")
                
                self.postgres_conn.commit()
                logger.info("Updated PostgreSQL sequences")
                return True
        except Exception as e:
            logger.error(f"Failed to update sequences: {e}")
            self.postgres_conn.rollback()
            return False
    
    def run_migration(self, clear_existing=False):
        """Run the complete migration process"""
        logger.info("Starting SQLite to PostgreSQL migration...")
        
        # Connect to databases
        if not self.connect_databases():
            return False
        
        try:
            # Check SQLite database
            if not self.check_sqlite_database():
                logger.info("No data to migrate from SQLite")
                return True
            
            # Clear existing PostgreSQL data if requested
            if clear_existing:
                if not self.clear_postgres_data():
                    logger.warning("Failed to clear some PostgreSQL data, continuing anyway...")
            
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
            
            # Migrate data
            for table_name in migration_order:
                if not self.migrate_table_data(table_name):
                    logger.error(f"Migration failed at table: {table_name}")
            
            # Update sequences after all data is migrated
            if not self.update_sequences():
                logger.error("Failed to update sequences")
            
            logger.info("Migration completed!")
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