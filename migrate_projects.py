from app import app, db
from models import User, TimeEntry, Project, Team, Role
from sqlalchemy import text
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_projects():
    """Migration script to add project time logging functionality"""
    with app.app_context():
        logger.info("Starting migration for project time logging...")
        
        # Check if the project table exists
        try:
            # Create the project table if it doesn't exist
            db.engine.execute(text("""
                CREATE TABLE IF NOT EXISTS project (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    code VARCHAR(20) NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER NOT NULL,
                    team_id INTEGER,
                    start_date DATE,
                    end_date DATE,
                    FOREIGN KEY (created_by_id) REFERENCES user (id),
                    FOREIGN KEY (team_id) REFERENCES team (id)
                )
            """))
            logger.info("Project table created or already exists")
        except Exception as e:
            logger.error(f"Error creating project table: {e}")
            return
        
        # Check if the time_entry table has the project-related columns
        try:
            # Check if project_id and notes columns exist in time_entry
            result = db.engine.execute(text("PRAGMA table_info(time_entry)"))
            columns = [row[1] for row in result]
            
            if 'project_id' not in columns:
                db.engine.execute(text("ALTER TABLE time_entry ADD COLUMN project_id INTEGER REFERENCES project(id)"))
                logger.info("Added project_id column to time_entry table")
            
            if 'notes' not in columns:
                db.engine.execute(text("ALTER TABLE time_entry ADD COLUMN notes TEXT"))
                logger.info("Added notes column to time_entry table")
            
        except Exception as e:
            logger.error(f"Error updating time_entry table: {e}")
            return
        
        # Create some default projects for demonstration
        try:
            # Check if any projects exist
            existing_projects = Project.query.count()
            if existing_projects == 0:
                # Find an admin or supervisor user to be the creator
                admin_user = User.query.filter_by(is_admin=True).first()
                if not admin_user:
                    admin_user = User.query.filter(User.role.in_([Role.ADMIN, Role.SUPERVISOR])).first()
                
                if admin_user:
                    # Create some sample projects
                    sample_projects = [
                        {
                            'name': 'General Administration',
                            'code': 'ADMIN001',
                            'description': 'General administrative tasks and meetings',
                            'team_id': None,  # Available to all teams
                        },
                        {
                            'name': 'Development Project',
                            'code': 'DEV001',
                            'description': 'Software development and maintenance tasks',
                            'team_id': None,  # Available to all teams
                        },
                        {
                            'name': 'Customer Support',
                            'code': 'SUPPORT001',
                            'description': 'Customer service and technical support activities',
                            'team_id': None,  # Available to all teams
                        }
                    ]
                    
                    for proj_data in sample_projects:
                        project = Project(
                            name=proj_data['name'],
                            code=proj_data['code'],
                            description=proj_data['description'],
                            team_id=proj_data['team_id'],
                            created_by_id=admin_user.id,
                            is_active=True
                        )
                        db.session.add(project)
                    
                    db.session.commit()
                    logger.info(f"Created {len(sample_projects)} sample projects")
                else:
                    logger.warning("No admin or supervisor user found to create sample projects")
            else:
                logger.info(f"Found {existing_projects} existing projects, skipping sample creation")
        
        except Exception as e:
            logger.error(f"Error creating sample projects: {e}")
            db.session.rollback()
        
        # Update database schema to match the current models
        try:
            db.create_all()
            logger.info("Database schema updated successfully")
        except Exception as e:
            logger.error(f"Error updating database schema: {e}")
            return
        
        # Verify the migration
        try:
            # Check if we can query the new tables and columns
            project_count = Project.query.count()
            logger.info(f"Project table accessible with {project_count} projects")
            
            # Check if time_entry has the new columns
            result = db.engine.execute(text("PRAGMA table_info(time_entry)"))
            columns = [row[1] for row in result]
            
            required_columns = ['project_id', 'notes']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.error(f"Missing columns in time_entry: {missing_columns}")
                return
            else:
                logger.info("All required columns present in time_entry table")
            
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return
        
        logger.info("Project time logging migration completed successfully!")
        print("\n" + "="*60)
        print("PROJECT TIME LOGGING FEATURE ENABLED")
        print("="*60)
        print("✅ Project management interface available for Admins/Supervisors")
        print("✅ Time tracking with optional project selection")
        print("✅ Project-based reporting and filtering")
        print("✅ Enhanced export functionality with project data")
        print("\nAccess project management via:")
        print("- Admin dropdown → Manage Projects")
        print("- Supervisor dropdown → Manage Projects")
        print("="*60)

def rollback_projects():
    """Rollback migration (removes project functionality)"""
    with app.app_context():
        logger.warning("Rolling back project time logging migration...")
        
        try:
            # Drop the project table
            db.engine.execute(text("DROP TABLE IF EXISTS project"))
            logger.info("Dropped project table")
            
            # Note: SQLite doesn't support dropping columns, so we can't remove
            # project_id and notes columns from time_entry table
            logger.warning("Note: project_id and notes columns in time_entry table cannot be removed due to SQLite limitations")
            logger.warning("These columns will remain but will not be used")
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return
        
        logger.info("Project time logging rollback completed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_projects()
    else:
        migrate_projects()