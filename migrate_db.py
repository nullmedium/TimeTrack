from app import app, db
import sqlite3
import os
from models import User, TimeEntry, WorkConfig, SystemSettings, Team, Role, Project, Company, AccountType
from werkzeug.security import generate_password_hash
from datetime import datetime

def migrate_database():
    db_path = 'timetrack.db'

    # Check if database exists
    if not os.path.exists(db_path):
        print("Database doesn't exist. Creating new database.")
        with app.app_context():
            db.create_all()
            
            # Initialize system settings
            init_system_settings()
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
    
    # Add role column to user table if it doesn't exist
    if 'role' not in user_columns:
        print("Adding role column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(50) DEFAULT 'Team Member'")
    
    # Add team_id column to user table if it doesn't exist
    if 'team_id' not in user_columns:
        print("Adding team_id column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN team_id INTEGER")
    
    # Add freelancer support columns to user table
    if 'account_type' not in user_columns:
        print("Adding account_type column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN account_type VARCHAR(20) DEFAULT 'COMPANY_USER'")
        
    if 'business_name' not in user_columns:
        print("Adding business_name column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN business_name VARCHAR(100)")
    
    # Add company_id to user table for multi-tenancy
    if 'company_id' not in user_columns:
        print("Adding company_id column to user table...")
        # Note: We can't add NOT NULL constraint to existing table, so allow NULL initially
        cursor.execute("ALTER TABLE user ADD COLUMN company_id INTEGER")
    
    # Add 2FA columns to user table if they don't exist
    if 'two_factor_enabled' not in user_columns:
        print("Adding two_factor_enabled column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0")
    
    if 'two_factor_secret' not in user_columns:
        print("Adding two_factor_secret column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN two_factor_secret VARCHAR(32)")

    # Check if the team table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team'")
    if not cursor.fetchone():
        print("Creating team table...")
        cursor.execute("""
        CREATE TABLE team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            description VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # Check if the system_settings table exists
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
        
    # Check if the project table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project'")
    if not cursor.fetchone():
        print("Creating project table...")
        cursor.execute("""
        CREATE TABLE project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            code VARCHAR(20) NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by_id INTEGER NOT NULL,
            team_id INTEGER,
            start_date DATE,
            end_date DATE,
            FOREIGN KEY (created_by_id) REFERENCES user (id),
            FOREIGN KEY (team_id) REFERENCES team (id)
        )
        """)

    # Check if the company table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company'")
    if not cursor.fetchone():
        print("Creating company table...")
        cursor.execute("""
        CREATE TABLE company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            slug VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_personal BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            max_users INTEGER DEFAULT 100
        )
        """)
    else:
        # Check if company table has freelancer columns
        cursor.execute("PRAGMA table_info(company)")
        company_columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_personal' not in company_columns:
            print("Adding is_personal column to company table...")
            cursor.execute("ALTER TABLE company ADD COLUMN is_personal BOOLEAN DEFAULT 0")

    # Add project-related columns to time_entry table
    cursor.execute("PRAGMA table_info(time_entry)")
    time_entry_columns = [column[1] for column in cursor.fetchall()]
    
    if 'project_id' not in time_entry_columns:
        print("Adding project_id column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN project_id INTEGER")
        
    if 'notes' not in time_entry_columns:
        print("Adding notes column to time_entry...")
        cursor.execute("ALTER TABLE time_entry ADD COLUMN notes TEXT")

    # Commit changes and close connection
    conn.commit()
    conn.close()

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Initialize system settings
        init_system_settings()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@timetrack.local',
                is_verified=True,  # Admin is automatically verified
                role=Role.ADMIN,
                two_factor_enabled=False
            )
            admin.set_password('admin')  # Default password, should be changed
            db.session.add(admin)
            db.session.commit()
            print("Created admin user with username 'admin' and password 'admin'")
            print("Please change the admin password after first login!")
        else:
            # Make sure existing admin user is verified and has correct role
            if not hasattr(admin, 'is_verified') or not admin.is_verified:
                admin.is_verified = True
            if not hasattr(admin, 'role') or admin.role is None:
                admin.role = Role.ADMIN
            if not hasattr(admin, 'two_factor_enabled') or admin.two_factor_enabled is None:
                admin.two_factor_enabled = False
            db.session.commit()
            print("Updated existing admin user with new fields")
        
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
        
        # Update existing users with default role and 2FA settings
        users_to_update = User.query.all()
        updated_count = 0
        for user in users_to_update:
            updated = False
            if not hasattr(user, 'role') or user.role is None:
                user.role = Role.TEAM_MEMBER
                updated = True
            if not hasattr(user, 'two_factor_enabled') or user.two_factor_enabled is None:
                user.two_factor_enabled = False
                updated = True
            if updated:
                updated_count += 1
        
        # Check if any system admin users exist
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()
        if system_admin_count == 0:
            print("No system administrators found. Consider promoting a user to SYSTEM_ADMIN role manually.")
            print("Use: UPDATE user SET role = 'System Administrator' WHERE username = 'your_username';")
        else:
            print(f"Found {system_admin_count} system administrator(s)")
            
        db.session.commit()
        print(f"Associated {len(orphan_entries)} existing time entries with admin user")
        print(f"Associated {len(orphan_configs)} existing work configs with admin user")
        print(f"Marked {len(existing_users)} existing users as verified")
        print(f"Updated {updated_count} users with default role and 2FA settings")
        
        # Create sample projects if none exist
        existing_projects = Project.query.count()
        if existing_projects == 0 and admin:
            sample_projects = [
                {
                    'name': 'General Administration',
                    'code': 'ADMIN001',
                    'description': 'General administrative tasks and meetings',
                    'team_id': None,
                },
                {
                    'name': 'Development Project',
                    'code': 'DEV001',
                    'description': 'Software development and maintenance tasks',
                    'team_id': None,
                },
                {
                    'name': 'Customer Support',
                    'code': 'SUPPORT001',
                    'description': 'Customer service and technical support activities',
                    'team_id': None,
                }
            ]
            
            for proj_data in sample_projects:
                project = Project(
                    name=proj_data['name'],
                    code=proj_data['code'],
                    description=proj_data['description'],
                    team_id=proj_data['team_id'],
                    created_by_id=admin.id,
                    is_active=True
                )
                db.session.add(project)
            
            db.session.commit()
            print(f"Created {len(sample_projects)} sample projects")

def init_system_settings():
    """Initialize system settings with default values if they don't exist"""
    # Check if registration_enabled setting exists
    reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
    if not reg_setting:
        print("Adding registration_enabled system setting...")
        reg_setting = SystemSettings(
            key='registration_enabled',
            value='true',  # Default to enabled
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
            value='true',  # Default to enabled for security
            description='Controls whether email verification is required for new user accounts'
        )
        db.session.add(email_verification_setting)
        db.session.commit()
        print("Email verification setting initialized to enabled")

if __name__ == "__main__":
    migrate_database()
    print("Database migration completed")