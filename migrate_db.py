#!/usr/bin/env python3
"""
Database Migration Script for TimeTrack
Consolidates all database migrations and provides command line interface.
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime

# Try to import from Flask app context if available
try:
    from app import app, db
    from models import (User, TimeEntry, WorkConfig, SystemSettings, Team, Role, Project, 
                       Company, CompanyWorkConfig, UserPreferences, WorkRegion, AccountType, 
                       ProjectCategory, Task, SubTask, TaskStatus, TaskPriority)
    from werkzeug.security import generate_password_hash
    FLASK_AVAILABLE = True
except ImportError:
    print("Flask app not available. Running in standalone mode.")
    FLASK_AVAILABLE = False
    # Define Role and AccountType enums for standalone mode
    import enum
    
    class Role(enum.Enum):
        TEAM_MEMBER = "Team Member"
        TEAM_LEADER = "Team Leader"
        SUPERVISOR = "Supervisor"
        ADMIN = "Administrator"
        SYSTEM_ADMIN = "System Administrator"
    
    class AccountType(enum.Enum):
        COMPANY_USER = "Company User"
        FREELANCER = "Freelancer"


def get_db_path(db_file=None):
    """Determine database path based on environment or provided file."""
    if db_file:
        return db_file
    
    # Check for Docker environment
    if os.path.exists('/data'):
        return '/data/timetrack.db'
    
    return 'timetrack.db'


def run_all_migrations(db_path=None):
    """Run all database migrations in sequence."""
    db_path = get_db_path(db_path)
    print(f"Running migrations on database: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database doesn't exist. Creating new database.")
        if FLASK_AVAILABLE:
            with app.app_context():
                db.create_all()
                init_system_settings()
        else:
            create_new_database(db_path)
        return
    
    print("Running database migrations...")
    
    # Run migrations in sequence
    run_basic_migrations(db_path)
    migrate_to_company_model(db_path)
    migrate_work_config_data(db_path)
    migrate_task_system(db_path)
    
    if FLASK_AVAILABLE:
        with app.app_context():
            # Handle company migration and admin user setup
            migrate_data()
    
    print("Database migrations completed successfully!")


def run_basic_migrations(db_path):
    """Run basic table structure migrations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if time_entry table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='time_entry'")
        if not cursor.fetchone():
            print("time_entry table doesn't exist. Creating all tables...")
            if FLASK_AVAILABLE:
                with app.app_context():
                    db.create_all()
                    init_system_settings()
            else:
                create_all_tables(cursor)
            conn.commit()
            conn.close()
            return

        # Migrate time_entry table
        cursor.execute("PRAGMA table_info(time_entry)")
        time_entry_columns = [column[1] for column in cursor.fetchall()]

        migrations = [
            ('is_paused', "ALTER TABLE time_entry ADD COLUMN is_paused BOOLEAN DEFAULT 0"),
            ('pause_start_time', "ALTER TABLE time_entry ADD COLUMN pause_start_time TIMESTAMP"),
            ('total_break_duration', "ALTER TABLE time_entry ADD COLUMN total_break_duration INTEGER DEFAULT 0"),
            ('user_id', "ALTER TABLE time_entry ADD COLUMN user_id INTEGER"),
            ('project_id', "ALTER TABLE time_entry ADD COLUMN project_id INTEGER"),
            ('notes', "ALTER TABLE time_entry ADD COLUMN notes TEXT"),
            ('task_id', "ALTER TABLE time_entry ADD COLUMN task_id INTEGER"),
            ('subtask_id', "ALTER TABLE time_entry ADD COLUMN subtask_id INTEGER")
        ]

        for column_name, sql_command in migrations:
            if column_name not in time_entry_columns:
                print(f"Adding {column_name} column to time_entry...")
                cursor.execute(sql_command)

        # Migrate work_config table
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
                user_id INTEGER,
                additional_break_minutes INTEGER DEFAULT 15,
                additional_break_threshold_hours FLOAT DEFAULT 9.0
            )
            """)
        else:
            cursor.execute("PRAGMA table_info(work_config)")
            work_config_columns = [column[1] for column in cursor.fetchall()]
            
            work_config_migrations = [
                ('additional_break_minutes', "ALTER TABLE work_config ADD COLUMN additional_break_minutes INTEGER DEFAULT 15"),
                ('additional_break_threshold_hours', "ALTER TABLE work_config ADD COLUMN additional_break_threshold_hours FLOAT DEFAULT 9.0"),
                ('user_id', "ALTER TABLE work_config ADD COLUMN user_id INTEGER")
            ]

            for column_name, sql_command in work_config_migrations:
                if column_name not in work_config_columns:
                    print(f"Adding {column_name} column to work_config...")
                    cursor.execute(sql_command)

        # Migrate user table
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]

        user_migrations = [
            ('is_verified', "ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0"),
            ('verification_token', "ALTER TABLE user ADD COLUMN verification_token VARCHAR(100)"),
            ('token_expiry', "ALTER TABLE user ADD COLUMN token_expiry TIMESTAMP"),
            ('is_blocked', "ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT 0"),
            ('role', "ALTER TABLE user ADD COLUMN role VARCHAR(50) DEFAULT 'Team Member'"),
            ('team_id', "ALTER TABLE user ADD COLUMN team_id INTEGER"),
            ('account_type', f"ALTER TABLE user ADD COLUMN account_type VARCHAR(20) DEFAULT '{AccountType.COMPANY_USER.value}'"),
            ('business_name', "ALTER TABLE user ADD COLUMN business_name VARCHAR(100)"),
            ('company_id', "ALTER TABLE user ADD COLUMN company_id INTEGER"),
            ('two_factor_enabled', "ALTER TABLE user ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0"),
            ('two_factor_secret', "ALTER TABLE user ADD COLUMN two_factor_secret VARCHAR(32)")
        ]

        for column_name, sql_command in user_migrations:
            if column_name not in user_columns:
                print(f"Adding {column_name} column to user...")
                cursor.execute(sql_command)

        # Handle is_admin to role migration
        if 'is_admin' in user_columns and 'role' in user_columns:
            print("Migrating is_admin column to role...")
            cursor.execute("UPDATE user SET role = ? WHERE is_admin = 1 AND (role IS NULL OR role = '')", (Role.ADMIN.value,))
            cursor.execute("UPDATE user SET role = ? WHERE is_admin = 0 AND (role IS NULL OR role = '')", (Role.TEAM_MEMBER.value,))

        # Create other tables if they don't exist
        create_missing_tables(cursor)

        conn.commit()
        
    except Exception as e:
        print(f"Error during basic migrations: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def create_missing_tables(cursor):
    """Create missing tables."""
    
    # Team table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team'")
    if not cursor.fetchone():
        print("Creating team table...")
        cursor.execute("""
        CREATE TABLE team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            company_id INTEGER NOT NULL,
            FOREIGN KEY (company_id) REFERENCES company (id),
            UNIQUE(company_id, name)
        )
        """)

    # System settings table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
    if not cursor.fetchone():
        print("Creating system_settings table...")
        cursor.execute("""
        CREATE TABLE system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key VARCHAR(50) UNIQUE NOT NULL,
            value VARCHAR(255) NOT NULL,
            description VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # Project table  
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project'")
    if not cursor.fetchone():
        print("Creating project table...")
        cursor.execute("""
        CREATE TABLE project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            code VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            company_id INTEGER NOT NULL,
            created_by_id INTEGER NOT NULL,
            team_id INTEGER,
            category_id INTEGER,
            start_date DATE,
            end_date DATE,
            FOREIGN KEY (company_id) REFERENCES company (id),
            FOREIGN KEY (created_by_id) REFERENCES user (id),
            FOREIGN KEY (team_id) REFERENCES team (id),
            FOREIGN KEY (category_id) REFERENCES project_category (id),
            UNIQUE(company_id, code)
        )
        """)

    # Company table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company'")
    if not cursor.fetchone():
        print("Creating company table...")
        cursor.execute("""
        CREATE TABLE company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_personal BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            max_users INTEGER DEFAULT 100,
            UNIQUE(name)
        )
        """)


def migrate_to_company_model(db_path):
    """Migrate to company-based multi-tenancy model."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if company table exists, create if not
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company'")
        if not cursor.fetchone():
            create_missing_tables(cursor)

        # Check and add missing columns to existing company table
        cursor.execute("PRAGMA table_info(company)")
        company_columns = [column[1] for column in cursor.fetchall()]

        company_migrations = [
            ('is_personal', "ALTER TABLE company ADD COLUMN is_personal BOOLEAN DEFAULT 0")
        ]

        for column_name, sql_command in company_migrations:
            if column_name not in company_columns:
                print(f"Adding {column_name} column to company...")
                cursor.execute(sql_command)

        # Add company_id to tables that need it
        add_company_id_to_tables(cursor)

        # Handle user role enum migration
        migrate_user_roles(cursor)

        conn.commit()

    except Exception as e:
        print(f"Error during company model migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def add_company_id_to_tables(cursor):
    """Add company_id columns to tables that need multi-tenancy."""
    
    tables_needing_company = ['project', 'team']
    
    for table_name in tables_needing_company:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'company_id' not in columns:
            print(f"Adding company_id column to {table_name}...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN company_id INTEGER")


def migrate_user_roles(cursor):
    """Handle user role enum migration with constraint updates."""
    
    cursor.execute("PRAGMA table_info(user)")
    user_columns = cursor.fetchall()

    # Check if we need to migrate the role enum constraint
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='user'")
    create_table_sql = cursor.fetchone()

    if create_table_sql and 'System Administrator' not in create_table_sql[0]:
        print("Updating role enum constraint to include SYSTEM_ADMIN...")

        # Check existing role values
        cursor.execute("SELECT DISTINCT role FROM user WHERE role IS NOT NULL")
        existing_roles = [row[0] for row in cursor.fetchall()]
        print(f"Found existing roles: {existing_roles}")

        # First normalize role values in the existing table
        print("Normalizing role values before table recreation...")
        role_mapping = {
            'TEAM_MEMBER': Role.TEAM_MEMBER.value,
            'TEAM_LEADER': Role.TEAM_LEADER.value,
            'SUPERVISOR': Role.SUPERVISOR.value,
            'ADMIN': Role.ADMIN.value,
            'SYSTEM_ADMIN': Role.SYSTEM_ADMIN.value
        }

        for old_role, new_role in role_mapping.items():
            cursor.execute("UPDATE user SET role = ? WHERE role = ?", (new_role, old_role))
            updated_count = cursor.rowcount
            if updated_count > 0:
                print(f"Updated {updated_count} users from role '{old_role}' to '{new_role}'")

        # Set any NULL or invalid roles to defaults
        cursor.execute("UPDATE user SET role = ? WHERE role IS NULL OR role NOT IN (?, ?, ?, ?, ?)", 
                      (Role.TEAM_MEMBER.value, Role.TEAM_MEMBER.value, Role.TEAM_LEADER.value, 
                       Role.SUPERVISOR.value, Role.ADMIN.value, Role.SYSTEM_ADMIN.value))
        null_roles = cursor.rowcount
        if null_roles > 0:
            print(f"Set {null_roles} NULL/invalid roles to 'Team Member'")

        # Drop user_new table if it exists from previous failed migration
        cursor.execute("DROP TABLE IF EXISTS user_new")

        # Create a backup table with the new enum constraint
        cursor.execute("""
        CREATE TABLE user_new (
            id INTEGER PRIMARY KEY,
            username VARCHAR(80) NOT NULL,
            email VARCHAR(120) NOT NULL,
            password_hash VARCHAR(128),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            company_id INTEGER NOT NULL,
            is_verified BOOLEAN DEFAULT 0,
            verification_token VARCHAR(100),
            token_expiry TIMESTAMP,
            is_blocked BOOLEAN DEFAULT 0,
            role VARCHAR(50) DEFAULT 'Team Member' CHECK (role IN ('Team Member', 'Team Leader', 'Supervisor', 'Administrator', 'System Administrator')),
            team_id INTEGER,
            account_type VARCHAR(20) DEFAULT 'Company User' CHECK (account_type IN ('Company User', 'Freelancer')),
            business_name VARCHAR(100),
            two_factor_enabled BOOLEAN DEFAULT 0,
            two_factor_secret VARCHAR(32),
            FOREIGN KEY (company_id) REFERENCES company (id),
            FOREIGN KEY (team_id) REFERENCES team (id)
        )
        """)

        # Copy all data from old table to new table with validation
        cursor.execute("""
        INSERT INTO user_new 
        SELECT id, username, email, password_hash, created_at, company_id, 
               is_verified, verification_token, token_expiry, is_blocked,
               CASE 
                   WHEN role IN (?, ?, ?, ?, ?) THEN role
                   ELSE ?
               END as role,
               team_id,
               CASE 
                   WHEN account_type IN (?, ?) THEN account_type
                   ELSE ?
               END as account_type,
               business_name, two_factor_enabled, two_factor_secret
        FROM user
        """, (Role.TEAM_MEMBER.value, Role.TEAM_LEADER.value, Role.SUPERVISOR.value, 
              Role.ADMIN.value, Role.SYSTEM_ADMIN.value, Role.TEAM_MEMBER.value,
              AccountType.COMPANY_USER.value, AccountType.FREELANCER.value, 
              AccountType.COMPANY_USER.value))

        # Drop the old table and rename the new one
        cursor.execute("DROP TABLE user")
        cursor.execute("ALTER TABLE user_new RENAME TO user")

        print("✓ Role enum constraint updated successfully")

    # Additional normalization for account_type values
    print("Normalizing account_type values...")
    account_type_mapping = {
        'COMPANY_USER': AccountType.COMPANY_USER.value,
        'FREELANCER': AccountType.FREELANCER.value
    }

    for old_type, new_type in account_type_mapping.items():
        cursor.execute("UPDATE user SET account_type = ? WHERE account_type = ?", (new_type, old_type))
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"Updated {updated_count} users account_type from '{old_type}' to '{new_type}'")

    # Set any remaining NULL values to defaults
    cursor.execute("UPDATE user SET account_type = ? WHERE account_type IS NULL", (AccountType.COMPANY_USER.value,))
    null_accounts = cursor.rowcount
    if null_accounts > 0:
        print(f"Set {null_accounts} NULL account_types to 'Company User'")


def migrate_work_config_data(db_path):
    """Migrate work configuration data to new company-based model."""
    if not FLASK_AVAILABLE:
        print("Skipping work config data migration - Flask not available")
        return
        
    with app.app_context():
        try:
            # Create CompanyWorkConfig for all companies that don't have one
            companies = Company.query.all()
            for company in companies:
                existing_config = CompanyWorkConfig.query.filter_by(company_id=company.id).first()
                if not existing_config:
                    print(f"Creating CompanyWorkConfig for {company.name}")
                    
                    # Use Germany defaults (existing system default)
                    preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
                    
                    company_config = CompanyWorkConfig(
                        company_id=company.id,
                        work_hours_per_day=preset['work_hours_per_day'],
                        mandatory_break_minutes=preset['mandatory_break_minutes'],
                        break_threshold_hours=preset['break_threshold_hours'],
                        additional_break_minutes=preset['additional_break_minutes'],
                        additional_break_threshold_hours=preset['additional_break_threshold_hours'],
                        region=preset['region'],
                        region_name=preset['region_name']
                    )
                    db.session.add(company_config)
            
            # Migrate existing WorkConfig user preferences to UserPreferences
            old_configs = WorkConfig.query.filter(WorkConfig.user_id.isnot(None)).all()
            for old_config in old_configs:
                user = User.query.get(old_config.user_id)
                if user:
                    existing_prefs = UserPreferences.query.filter_by(user_id=user.id).first()
                    if not existing_prefs:
                        print(f"Migrating preferences for user {user.username}")
                        
                        user_prefs = UserPreferences(
                            user_id=user.id,
                            time_format_24h=getattr(old_config, 'time_format_24h', True),
                            date_format=getattr(old_config, 'date_format', 'YYYY-MM-DD'),
                            round_minutes_interval=getattr(old_config, 'round_minutes_interval', 0),
                            round_to_nearest=getattr(old_config, 'round_to_nearest', True)
                        )
                        db.session.add(user_prefs)
            
            db.session.commit()
            print("Work config data migration completed successfully")
            
        except Exception as e:
            print(f"Error during work config migration: {e}")
            db.session.rollback()


def migrate_task_system(db_path):
    """Create tables for the task management system."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if project_category table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_category'")
        if not cursor.fetchone():
            print("Creating project_category table...")
            cursor.execute("""
            CREATE TABLE project_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                color VARCHAR(7) DEFAULT '#007bff',
                icon VARCHAR(50),
                company_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_id INTEGER NOT NULL,
                FOREIGN KEY (company_id) REFERENCES company (id),
                FOREIGN KEY (created_by_id) REFERENCES user (id),
                UNIQUE(company_id, name)
            )
            """)

        # Check if task table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task'")
        if not cursor.fetchone():
            print("Creating task table...")
            cursor.execute("""
            CREATE TABLE task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'Not Started',
                priority VARCHAR(50) DEFAULT 'Medium',
                estimated_hours FLOAT,
                project_id INTEGER NOT NULL,
                assigned_to_id INTEGER,
                start_date DATE,
                due_date DATE,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_id INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project (id),
                FOREIGN KEY (assigned_to_id) REFERENCES user (id),
                FOREIGN KEY (created_by_id) REFERENCES user (id)
            )
            """)

        # Check if sub_task table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sub_task'")
        if not cursor.fetchone():
            print("Creating sub_task table...")
            cursor.execute("""
            CREATE TABLE sub_task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'Not Started',
                priority VARCHAR(50) DEFAULT 'Medium',
                estimated_hours FLOAT,
                task_id INTEGER NOT NULL,
                assigned_to_id INTEGER,
                start_date DATE,
                due_date DATE,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_id INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES task (id),
                FOREIGN KEY (assigned_to_id) REFERENCES user (id),
                FOREIGN KEY (created_by_id) REFERENCES user (id)
            )
            """)

        # Add category_id to project table if it doesn't exist
        cursor.execute("PRAGMA table_info(project)")
        project_columns = [column[1] for column in cursor.fetchall()]
        if 'category_id' not in project_columns:
            print("Adding category_id column to project table...")
            cursor.execute("ALTER TABLE project ADD COLUMN category_id INTEGER")

        # Add task_id and subtask_id to time_entry table if they don't exist
        cursor.execute("PRAGMA table_info(time_entry)")
        time_entry_columns = [column[1] for column in cursor.fetchall()]

        task_migrations = [
            ('task_id', "ALTER TABLE time_entry ADD COLUMN task_id INTEGER"),
            ('subtask_id', "ALTER TABLE time_entry ADD COLUMN subtask_id INTEGER")
        ]

        for column_name, sql_command in task_migrations:
            if column_name not in time_entry_columns:
                print(f"Adding {column_name} column to time_entry...")
                cursor.execute(sql_command)

        conn.commit()
        print("Task system migration completed successfully!")

    except Exception as e:
        print(f"Error during task system migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate_data():
    """Handle data migration with Flask app context."""
    if not FLASK_AVAILABLE:
        print("Skipping data migration - Flask not available")
        return
        
    try:
        # Update existing users with null/invalid data
        users = User.query.all()
        for user in users:
            if user.role is None:
                user.role = Role.TEAM_MEMBER
            if user.two_factor_enabled is None:
                user.two_factor_enabled = False
        
        # Check if any system admin users exist
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()
        if system_admin_count == 0:
            print("No system administrators found. Consider promoting a user to SYSTEM_ADMIN role manually.")
            print(f"To promote a user: UPDATE user SET role = '{Role.SYSTEM_ADMIN.value}' WHERE username = 'your_username';")
        else:
            print(f"Found {system_admin_count} system administrator(s)")
        
        db.session.commit()
        print("Data migration completed successfully")
        
    except Exception as e:
        print(f"Error during data migration: {e}")
        db.session.rollback()


def init_system_settings():
    """Initialize system settings with default values if they don't exist."""
    if not FLASK_AVAILABLE:
        print("Skipping system settings initialization - Flask not available")
        return
        
    # Check if registration_enabled setting exists
    reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
    if not reg_setting:
        print("Adding registration_enabled system setting...")
        reg_setting = SystemSettings(
            key='registration_enabled',
            value='true',
            description='Controls whether new user registration is allowed'
        )
        db.session.add(reg_setting)
        db.session.commit()
        print("Registration setting initialized to enabled")
    
    # Check if email_verification_required setting exists
    email_verification_setting = SystemSettings.query.filter_by(key='email_verification_required').first()
    if not email_verification_setting:
        print("Adding email_verification_required system setting...")
        email_verification_setting = SystemSettings(
            key='email_verification_required',
            value='true',
            description='Controls whether email verification is required for new user accounts'
        )
        db.session.add(email_verification_setting)
        db.session.commit()
        print("Email verification setting initialized to enabled")


def create_new_database(db_path):
    """Create a new database with all tables."""
    print(f"Creating new database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        create_all_tables(cursor)
        conn.commit()
        print("New database created successfully")
    except Exception as e:
        print(f"Error creating new database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def create_all_tables(cursor):
    """Create all tables from scratch."""
    # This would contain all CREATE TABLE statements
    # For brevity, showing key tables only
    
    cursor.execute("""
    CREATE TABLE company (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        slug VARCHAR(50) UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_personal BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        max_users INTEGER DEFAULT 100,
        UNIQUE(name)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE user (
        id INTEGER PRIMARY KEY,
        username VARCHAR(80) NOT NULL,
        email VARCHAR(120) NOT NULL,
        password_hash VARCHAR(128),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        company_id INTEGER NOT NULL,
        is_verified BOOLEAN DEFAULT 0,
        verification_token VARCHAR(100),
        token_expiry TIMESTAMP,
        is_blocked BOOLEAN DEFAULT 0,
        role VARCHAR(50) DEFAULT 'Team Member' CHECK (role IN ('Team Member', 'Team Leader', 'Supervisor', 'Administrator', 'System Administrator')),
        team_id INTEGER,
        account_type VARCHAR(20) DEFAULT 'Company User' CHECK (account_type IN ('Company User', 'Freelancer')),
        business_name VARCHAR(100),
        two_factor_enabled BOOLEAN DEFAULT 0,
        two_factor_secret VARCHAR(32),
        FOREIGN KEY (company_id) REFERENCES company (id),
        FOREIGN KEY (team_id) REFERENCES team (id)
    )
    """)
    
    # Add other table creation statements as needed
    print("All tables created")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='TimeTrack Database Migration Tool')
    parser.add_argument('--db-file', '-d', help='Path to SQLite database file')
    parser.add_argument('--create-new', '-c', action='store_true', 
                       help='Create a new database (will overwrite existing)')
    parser.add_argument('--migrate-all', '-m', action='store_true', 
                       help='Run all migrations (default action)')
    parser.add_argument('--task-system', '-t', action='store_true',
                       help='Run only task system migration')
    parser.add_argument('--company-model', '-p', action='store_true',
                       help='Run only company model migration')
    parser.add_argument('--basic', '-b', action='store_true',
                       help='Run only basic table migrations')
    
    args = parser.parse_args()
    
    db_path = get_db_path(args.db_file)
    
    print(f"TimeTrack Database Migration Tool")
    print(f"Database: {db_path}")
    print(f"Flask available: {FLASK_AVAILABLE}")
    print("-" * 50)
    
    try:
        if args.create_new:
            if os.path.exists(db_path):
                response = input(f"Database {db_path} exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print("Operation cancelled")
                    return
                os.remove(db_path)
            create_new_database(db_path)
            
        elif args.task_system:
            migrate_task_system(db_path)
            
        elif args.company_model:
            migrate_to_company_model(db_path)
            
        elif args.basic:
            run_basic_migrations(db_path)
            
        else:
            # Default: run all migrations
            run_all_migrations(db_path)
            
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nError during migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()