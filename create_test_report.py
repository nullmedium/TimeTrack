#!/usr/bin/env python3
"""
Create a test report to verify the report engine is working
"""

from app import app, db
from models import User, SavedReport

def create_test_report():
    with app.app_context():
        # Get the first user
        user = User.query.first()
        if not user:
            print("No users found in database")
            return
            
        # Create a simple test report
        test_report = SavedReport(
            user_id=user.id,
            name="Test Time Summary Report",
            description="A test report to verify functionality",
            config={
                "components": [
                    {
                        "type": "metric",
                        "id": "total_hours",
                        "config": {
                            "label": "Total Hours",
                            "format": "hours"
                        }
                    },
                    {
                        "type": "chart",
                        "id": "time_series",
                        "config": {
                            "type": "line",
                            "title": "Daily Hours"
                        }
                    }
                ]
            }
        )
        
        db.session.add(test_report)
        db.session.commit()
        
        print(f"Created test report with ID: {test_report.id}")
        print(f"Report name: {test_report.name}")
        print(f"User: {user.username}")

if __name__ == "__main__":
    create_test_report()