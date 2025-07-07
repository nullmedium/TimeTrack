#!/usr/bin/env python3
"""
Add company invitations table for email-based registration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models import db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Add company_invitation table"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////data/timetrack.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create company_invitation table
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS company_invitation (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES company(id),
                    email VARCHAR(120) NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    role VARCHAR(50) DEFAULT 'Team Member',
                    invited_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    accepted BOOLEAN DEFAULT FALSE,
                    accepted_at TIMESTAMP,
                    accepted_by_user_id INTEGER REFERENCES "user"(id)
                );
            """)
            
            db.session.execute(create_table_sql)
            
            # Create indexes for better performance
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_invitation_token ON company_invitation(token);"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_invitation_email ON company_invitation(email);"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_invitation_company ON company_invitation(company_id);"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_invitation_expires ON company_invitation(expires_at);"))
            
            db.session.commit()
            logger.info("Successfully created company_invitation table")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating company_invitation table: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)