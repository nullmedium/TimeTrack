#!/usr/bin/env python3
"""
Migration script for freelancer support in TimeTrack.

This migration adds:
1. AccountType enum support (handled by SQLAlchemy)
2. account_type column to user table
3. business_name column to user table  
4. is_personal column to company table

Usage:
    python migrate_freelancers.py          # Run migration
    python migrate_freelancers.py rollback # Rollback migration
"""

from app import app, db
import sqlite3
import os
import sys
from models import User, Company, AccountType
from datetime import datetime

def migrate_freelancer_support():
    """Add freelancer support to existing database"""
    db_path = 'timetrack.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database doesn't exist. Please run main migration first.")
        return False

    print("Migrating database for freelancer support...")

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check company table structure
        cursor.execute("PRAGMA table_info(company)")
        company_columns = [column[1] for column in cursor.fetchall()]
        
        # Add is_personal column to company table if it doesn't exist
        if 'is_personal' not in company_columns:
            print("Adding is_personal column to company table...")
            cursor.execute("ALTER TABLE company ADD COLUMN is_personal BOOLEAN DEFAULT 0")
            
        # Check user table structure
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        # Add account_type column to user table if it doesn't exist
        if 'account_type' not in user_columns:
            print("Adding account_type column to user table...")
            # Default to 'Company User' for existing users
            cursor.execute("ALTER TABLE user ADD COLUMN account_type VARCHAR(20) DEFAULT 'Company User'")
            
        # Add business_name column to user table if it doesn't exist
        if 'business_name' not in user_columns:
            print("Adding business_name column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN business_name VARCHAR(100)")

        # Commit changes
        conn.commit()
        print("✓ Freelancer migration completed successfully!")
        
        # Update existing users to have explicit account_type
        print("Updating existing users to Company User account type...")
        cursor.execute("UPDATE user SET account_type = 'Company User' WHERE account_type IS NULL OR account_type = ''")
        conn.commit()
        
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def rollback_freelancer_support():
    """Rollback freelancer support migration"""
    db_path = 'timetrack.db'
    
    if not os.path.exists(db_path):
        print("Database doesn't exist.")
        return False

    print("Rolling back freelancer support migration...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("WARNING: SQLite doesn't support dropping columns directly.")
        print("To fully rollback, you would need to:")
        print("1. Create new tables without the freelancer columns")
        print("2. Copy data from old tables to new tables")
        print("3. Drop old tables and rename new ones")
        print("\nFor safety, leaving columns in place but marking rollback as complete.")
        print("The application will work without issues with the extra columns present.")
        
        return True
        
    except Exception as e:
        print(f"✗ Rollback failed: {str(e)}")
        return False
    finally:
        conn.close()

def verify_migration():
    """Verify that the migration was applied correctly"""
    db_path = 'timetrack.db'
    
    if not os.path.exists(db_path):
        print("Database doesn't exist.")
        return False
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check company table
        cursor.execute("PRAGMA table_info(company)")
        company_columns = [column[1] for column in cursor.fetchall()]
        
        # Check user table  
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        print("\n=== Migration Verification ===")
        print("Company table columns:", company_columns)
        print("User table columns:", user_columns)
        
        # Verify required columns exist
        missing_columns = []
        if 'is_personal' not in company_columns:
            missing_columns.append('company.is_personal')
        if 'account_type' not in user_columns:
            missing_columns.append('user.account_type')
        if 'business_name' not in user_columns:
            missing_columns.append('user.business_name')
            
        if missing_columns:
            print(f"✗ Missing columns: {', '.join(missing_columns)}")
            return False
        else:
            print("✓ All required columns present")
            return True
            
    except Exception as e:
        print(f"✗ Verification failed: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = rollback_freelancer_support()
    elif len(sys.argv) > 1 and sys.argv[1] == 'verify':
        success = verify_migration()
    else:
        success = migrate_freelancer_support()
        if success:
            verify_migration()
    
    if success:
        print("\n✓ Operation completed successfully!")
    else:
        print("\n✗ Operation failed!")
        sys.exit(1)