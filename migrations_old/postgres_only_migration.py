#!/usr/bin/env python3
"""
PostgreSQL-only migration script for TimeTrack
Applies all schema changes from commit 4214e88 onward
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgresMigration:
    def __init__(self, database_url):
        self.database_url = database_url
        self.conn = None
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def execute_migration(self, name, sql_statements):
        """Execute a migration with proper error handling"""
        logger.info(f"Running migration: {name}")
        cursor = self.conn.cursor()
        
        try:
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
            self.conn.commit()
            logger.info(f"✓ {name} completed successfully")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ {name} failed: {e}")
            return False
        finally:
            cursor.close()
    
    def check_column_exists(self, table_name, column_name):
        """Check if a column exists in a table"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            )
        """, (table_name, column_name))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    
    def check_table_exists(self, table_name):
        """Check if a table exists"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    
    def check_enum_value_exists(self, enum_name, value):
        """Check if an enum value exists"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = %s 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = %s)
            )
        """, (value, enum_name))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    
    def run_all_migrations(self):
        """Run all migrations in order"""
        if not self.connect():
            return False
        
        success = True
        
        # 1. Add company.updated_at
        if not self.check_column_exists('company', 'updated_at'):
            success &= self.execute_migration("Add company.updated_at", [
                """
                ALTER TABLE company 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """,
                """
                UPDATE company SET updated_at = created_at WHERE updated_at IS NULL;
                """
            ])
        
        # 2. Add user columns for 2FA and avatar
        if not self.check_column_exists('user', 'two_factor_enabled'):
            success &= self.execute_migration("Add user 2FA and avatar columns", [
                """
                ALTER TABLE "user" 
                ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE,
                ADD COLUMN two_factor_secret VARCHAR(32),
                ADD COLUMN avatar_url VARCHAR(255);
                """
            ])
        
        # 3. Create company_invitation table
        if not self.check_table_exists('company_invitation'):
            success &= self.execute_migration("Create company_invitation table", [
                """
                CREATE TABLE company_invitation (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES company(id),
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    invited_by_id INTEGER REFERENCES "user"(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP,
                    used_by_id INTEGER REFERENCES "user"(id)
                );
                """,
                """
                CREATE INDEX idx_invitation_token ON company_invitation(token);
                """,
                """
                CREATE INDEX idx_invitation_company ON company_invitation(company_id);
                """,
                """
                CREATE INDEX idx_invitation_email ON company_invitation(email);
                """
            ])
        
        # 4. Add user_preferences columns
        if self.check_table_exists('user_preferences'):
            columns_to_add = [
                ('theme', 'VARCHAR(20) DEFAULT \'light\''),
                ('language', 'VARCHAR(10) DEFAULT \'en\''),
                ('timezone', 'VARCHAR(50) DEFAULT \'UTC\''),
                ('date_format', 'VARCHAR(20) DEFAULT \'YYYY-MM-DD\''),
                ('time_format', 'VARCHAR(10) DEFAULT \'24h\''),
                ('week_start', 'INTEGER DEFAULT 1'),
                ('show_weekends', 'BOOLEAN DEFAULT TRUE'),
                ('compact_mode', 'BOOLEAN DEFAULT FALSE'),
                ('email_notifications', 'BOOLEAN DEFAULT TRUE'),
                ('push_notifications', 'BOOLEAN DEFAULT FALSE'),
                ('task_reminders', 'BOOLEAN DEFAULT TRUE'),
                ('daily_summary', 'BOOLEAN DEFAULT FALSE'),
                ('weekly_report', 'BOOLEAN DEFAULT TRUE'),
                ('mention_notifications', 'BOOLEAN DEFAULT TRUE'),
                ('task_assigned_notifications', 'BOOLEAN DEFAULT TRUE'),
                ('task_completed_notifications', 'BOOLEAN DEFAULT FALSE'),
                ('sound_enabled', 'BOOLEAN DEFAULT TRUE'),
                ('keyboard_shortcuts', 'BOOLEAN DEFAULT TRUE'),
                ('auto_start_timer', 'BOOLEAN DEFAULT FALSE'),
                ('idle_time_detection', 'BOOLEAN DEFAULT TRUE'),
                ('pomodoro_enabled', 'BOOLEAN DEFAULT FALSE'),
                ('pomodoro_duration', 'INTEGER DEFAULT 25'),
                ('pomodoro_break', 'INTEGER DEFAULT 5')
            ]
            
            for col_name, col_def in columns_to_add:
                if not self.check_column_exists('user_preferences', col_name):
                    success &= self.execute_migration(f"Add user_preferences.{col_name}", [
                        f'ALTER TABLE user_preferences ADD COLUMN {col_name} {col_def};'
                    ])
        
        # 5. Add user_dashboard columns
        if self.check_table_exists('user_dashboard'):
            if not self.check_column_exists('user_dashboard', 'layout'):
                success &= self.execute_migration("Add user_dashboard layout columns", [
                    """
                    ALTER TABLE user_dashboard 
                    ADD COLUMN layout JSON DEFAULT '{}',
                    ADD COLUMN is_locked BOOLEAN DEFAULT FALSE;
                    """
                ])
        
        # 6. Add company_work_config columns
        if self.check_table_exists('company_work_config'):
            columns_to_add = [
                ('standard_hours_per_day', 'FLOAT DEFAULT 8.0'),
                ('standard_hours_per_week', 'FLOAT DEFAULT 40.0'),
                ('overtime_rate', 'FLOAT DEFAULT 1.5'),
                ('double_time_enabled', 'BOOLEAN DEFAULT FALSE'),
                ('double_time_threshold', 'FLOAT DEFAULT 12.0'),
                ('double_time_rate', 'FLOAT DEFAULT 2.0'),
                ('weekly_overtime_threshold', 'FLOAT DEFAULT 40.0'),
                ('weekly_overtime_rate', 'FLOAT DEFAULT 1.5'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for col_name, col_def in columns_to_add:
                if not self.check_column_exists('company_work_config', col_name):
                    success &= self.execute_migration(f"Add company_work_config.{col_name}", [
                        f'ALTER TABLE company_work_config ADD COLUMN {col_name} {col_def};'
                    ])
        
        # 7. Add company_settings columns
        if self.check_table_exists('company_settings'):
            columns_to_add = [
                ('work_week_start', 'INTEGER DEFAULT 1'),
                ('work_days', 'VARCHAR(20) DEFAULT \'1,2,3,4,5\''),
                ('time_tracking_mode', 'VARCHAR(20) DEFAULT \'flexible\''),
                ('allow_manual_time', 'BOOLEAN DEFAULT TRUE'),
                ('require_project_selection', 'BOOLEAN DEFAULT TRUE'),
                ('allow_future_entries', 'BOOLEAN DEFAULT FALSE'),
                ('max_hours_per_entry', 'FLOAT DEFAULT 24.0'),
                ('min_hours_per_entry', 'FLOAT DEFAULT 0.0'),
                ('round_time_to', 'INTEGER DEFAULT 1'),
                ('auto_break_deduction', 'BOOLEAN DEFAULT FALSE'),
                ('allow_overlapping_entries', 'BOOLEAN DEFAULT FALSE'),
                ('require_daily_notes', 'BOOLEAN DEFAULT FALSE'),
                ('enable_tasks', 'BOOLEAN DEFAULT TRUE'),
                ('enable_projects', 'BOOLEAN DEFAULT TRUE'),
                ('enable_teams', 'BOOLEAN DEFAULT TRUE'),
                ('enable_reports', 'BOOLEAN DEFAULT TRUE'),
                ('enable_invoicing', 'BOOLEAN DEFAULT FALSE'),
                ('enable_client_access', 'BOOLEAN DEFAULT FALSE'),
                ('default_currency', 'VARCHAR(3) DEFAULT \'USD\''),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for col_name, col_def in columns_to_add:
                if not self.check_column_exists('company_settings', col_name):
                    success &= self.execute_migration(f"Add company_settings.{col_name}", [
                        f'ALTER TABLE company_settings ADD COLUMN {col_name} {col_def};'
                    ])
        
        # 8. Add dashboard_widget columns
        if self.check_table_exists('dashboard_widget'):
            if not self.check_column_exists('dashboard_widget', 'config'):
                success &= self.execute_migration("Add dashboard_widget config columns", [
                    """
                    ALTER TABLE dashboard_widget 
                    ADD COLUMN config JSON DEFAULT '{}',
                    ADD COLUMN is_visible BOOLEAN DEFAULT TRUE;
                    """
                ])
        
        # 9. Update WorkRegion enum
        if not self.check_enum_value_exists('workregion', 'GERMANY'):
            success &= self.execute_migration("Add GERMANY to WorkRegion enum", [
                """
                ALTER TYPE workregion ADD VALUE IF NOT EXISTS 'GERMANY';
                """
            ])
        
        # 10. Update TaskStatus enum
        if not self.check_enum_value_exists('taskstatus', 'ARCHIVED'):
            success &= self.execute_migration("Add ARCHIVED to TaskStatus enum", [
                """
                ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED';
                """
            ])
        
        # 11. Update WidgetType enum
        widget_types_to_add = [
            'REVENUE_CHART', 'EXPENSE_CHART', 'PROFIT_CHART', 'CASH_FLOW',
            'INVOICE_STATUS', 'CLIENT_LIST', 'PROJECT_BUDGET', 'TEAM_CAPACITY',
            'SPRINT_BURNDOWN', 'VELOCITY_CHART', 'BACKLOG_STATUS', 'RELEASE_TIMELINE',
            'CODE_COMMITS', 'BUILD_STATUS', 'DEPLOYMENT_HISTORY', 'ERROR_RATE',
            'SYSTEM_HEALTH', 'USER_ACTIVITY', 'SECURITY_ALERTS', 'AUDIT_LOG'
        ]
        
        for widget_type in widget_types_to_add:
            if not self.check_enum_value_exists('widgettype', widget_type):
                success &= self.execute_migration(f"Add {widget_type} to WidgetType enum", [
                    f"ALTER TYPE widgettype ADD VALUE IF NOT EXISTS '{widget_type}';"
                ])
        
        self.close()
        
        if success:
            logger.info("\n✅ All migrations completed successfully!")
        else:
            logger.error("\n❌ Some migrations failed. Check the logs above.")
        
        return success


def main():
    """Main migration function"""
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return 1
    
    # Run migrations
    migration = PostgresMigration(database_url)
    success = migration.run_all_migrations()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())