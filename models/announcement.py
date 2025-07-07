"""
Announcement model for system-wide notifications
"""

from datetime import datetime
import json
from . import db


class Announcement(db.Model):
    """System-wide announcements"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Announcement properties
    is_active = db.Column(db.Boolean, default=True)
    is_urgent = db.Column(db.Boolean, default=False)  # For urgent announcements with different styling
    announcement_type = db.Column(db.String(20), default='info')  # info, warning, success, danger

    # Scheduling
    start_date = db.Column(db.DateTime, nullable=True)  # When to start showing
    end_date = db.Column(db.DateTime, nullable=True)    # When to stop showing

    # Targeting
    target_all_users = db.Column(db.Boolean, default=True)
    target_roles = db.Column(db.Text, nullable=True)  # JSON string of roles if not all users
    target_companies = db.Column(db.Text, nullable=True)  # JSON string of company IDs if not all companies

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<Announcement {self.title}>'

    def is_visible_now(self):
        """Check if announcement should be visible at current time"""
        if not self.is_active:
            return False

        now = datetime.now()

        # Check start date
        if self.start_date and now < self.start_date:
            return False

        # Check end date
        if self.end_date and now > self.end_date:
            return False

        return True

    def is_visible_to_user(self, user):
        """Check if announcement should be visible to specific user"""
        if not self.is_visible_now():
            return False

        # If targeting all users, show to everyone
        if self.target_all_users:
            return True

        # Check role targeting
        if self.target_roles:
            try:
                target_roles = json.loads(self.target_roles)
                if user.role.value not in target_roles:
                    return False
            except (json.JSONDecodeError, AttributeError):
                pass

        # Check company targeting
        if self.target_companies:
            try:
                target_companies = json.loads(self.target_companies)
                if user.company_id not in target_companies:
                    return False
            except (json.JSONDecodeError, AttributeError):
                pass

        return True

    @staticmethod
    def get_active_announcements_for_user(user):
        """Get all active announcements visible to a specific user"""
        announcements = Announcement.query.filter_by(is_active=True).all()
        return [ann for ann in announcements if ann.is_visible_to_user(user)]