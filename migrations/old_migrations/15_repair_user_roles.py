#!/usr/bin/env python3
"""
Repair user roles from string to enum values
"""

import os
import sys
import logging

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app, db
    from models import User, Role
except Exception as e:
    print(f"Error importing modules: {e}")
    print("This migration requires Flask app context. Skipping...")
    sys.exit(0)

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
                user.role = Role.TEAM_MEMBER
                fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            logger.info(f"Fixed roles for {fixed_count} users")
        else:
            logger.info("No role fixes needed")
        
        logger.info("Role repair completed")

if __name__ == "__main__":
    try:
        repair_user_roles()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)