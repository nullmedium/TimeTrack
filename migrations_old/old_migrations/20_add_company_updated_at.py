#!/usr/bin/env python3
"""
Add updated_at column to company table
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Add updated_at column to company table"""
    with app.app_context():
        try:
            # Check if we're using PostgreSQL or SQLite
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
            is_postgres = 'postgresql://' in database_url or 'postgres://' in database_url
            
            if is_postgres:
                # PostgreSQL migration
                logger.info("Running PostgreSQL migration to add updated_at to company table...")
                
                # Check if column exists
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'company' AND column_name = 'updated_at'
                """))
                
                if not result.fetchone():
                    logger.info("Adding updated_at column to company table...")
                    db.session.execute(text("""
                        ALTER TABLE company 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    
                    # Update existing rows to have updated_at = created_at
                    db.session.execute(text("""
                        UPDATE company 
                        SET updated_at = created_at 
                        WHERE updated_at IS NULL
                    """))
                    
                    db.session.commit()
                    logger.info("Successfully added updated_at column to company table")
                else:
                    logger.info("updated_at column already exists in company table")
            else:
                # SQLite migration
                logger.info("Running SQLite migration to add updated_at to company table...")
                
                # For SQLite, we need to check differently
                result = db.session.execute(text("PRAGMA table_info(company)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'updated_at' not in columns:
                    logger.info("Adding updated_at column to company table...")
                    db.session.execute(text("""
                        ALTER TABLE company 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    
                    # Update existing rows to have updated_at = created_at
                    db.session.execute(text("""
                        UPDATE company 
                        SET updated_at = created_at 
                        WHERE updated_at IS NULL
                    """))
                    
                    db.session.commit()
                    logger.info("Successfully added updated_at column to company table")
                else:
                    logger.info("updated_at column already exists in company table")
                    
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)