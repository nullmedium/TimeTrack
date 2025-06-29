from app import app, db
from models import User, Role
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_user_roles():
    with app.app_context():
        logger.info("Starting user role repair...")
        
        # Map string role values to enum values
        role_mapping = {
            'Team Member': Role.TEAM_MEMBER,
            'TEAM_MEMBER': Role.TEAM_MEMBER,
            'Team Leader': Role.TEAM_LEADER,
            'TEAM_LEADER': Role.TEAM_LEADER,
            'Supervisor': Role.SUPERVISOR,
            'SUPERVISOR': Role.SUPERVISOR,
            'Administrator': Role.ADMIN,
            'ADMIN': Role.ADMIN
        }
        
        users = User.query.all()
        fixed_count = 0
        
        for user in users:
            original_role = user.role
            
            # Fix role if it's a string or None
            if isinstance(user.role, str):
                user.role = role_mapping.get(user.role, Role.TEAM_MEMBER)
                fixed_count += 1
            elif user.role is None:
                user.role = Role.ADMIN if user.is_admin else Role.TEAM_MEMBER
                fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            logger.info(f"Fixed roles for {fixed_count} users")
        else:
            logger.info("No role fixes needed")
        
        logger.info("Role repair completed")

if __name__ == "__main__":
    repair_user_roles()