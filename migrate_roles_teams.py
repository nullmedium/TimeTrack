from app import app, db
from models import User, Team, Role, SystemSettings
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_roles_teams():
    with app.app_context():
        logger.info("Starting migration for roles and teams...")
        
        # Check if the team table exists
        try:
            # Create the team table if it doesn't exist
            db.engine.execute(text("""
                CREATE TABLE IF NOT EXISTS team (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("Team table created or already exists")
        except Exception as e:
            logger.error(f"Error creating team table: {e}")
            return
        
        # Check if the user table has the role and team_id columns
        try:
            # Check if role column exists
            result = db.engine.execute(text("PRAGMA table_info(user)"))
            columns = [row[1] for row in result]
            
            if 'role' not in columns:
                # Use the enum name instead of the value
                db.engine.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'TEAM_MEMBER'"))
                logger.info("Added role column to user table")
            
            if 'team_id' not in columns:
                db.engine.execute(text("ALTER TABLE user ADD COLUMN team_id INTEGER REFERENCES team(id)"))
                logger.info("Added team_id column to user table")
            
            # Create a default team for existing users
            default_team = Team.query.filter_by(name="Default Team").first()
            if not default_team:
                default_team = Team(name="Default Team", description="Default team for existing users")
                db.session.add(default_team)
                db.session.commit()
                logger.info("Created default team")
            
            # Map string role values to enum values
            role_mapping = {
                'Team Member': Role.TEAM_MEMBER,
                'TEAM_MEMBER': Role.TEAM_MEMBER,
                'Team Leader': Role.TEAM_LEADER,
                'TEAM_LEADER': Role.TEAM_LEADER,
                'Supervisor': Role.SUPERVISOR,
                'SUPERVISOR': Role.SUPERVISOR,
                'Administrator': Role.ADMIN,
                'admin': Role.ADMIN,
                'ADMIN': Role.ADMIN
            }
            
            # Assign all existing users to the default team and set role based on admin status
            users = User.query.all()
            for user in users:
                if user.team_id is None:
                    user.team_id = default_team.id
                
                # Handle role conversion properly
                if isinstance(user.role, str):
                    # Try to map the string to an enum value
                    user.role = role_mapping.get(user.role, Role.TEAM_MEMBER)
                elif user.role is None:
                    # Set default role 
                    user.role = Role.TEAM_MEMBER
            
            db.session.commit()
            logger.info(f"Assigned {len(users)} existing users to default team and updated roles")
            
        except Exception as e:
            logger.error(f"Error updating user table: {e}")
            return
        
        logger.info("Migration completed successfully")

if __name__ == "__main__":
    migrate_roles_teams()