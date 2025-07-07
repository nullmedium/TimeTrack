"""
Work configuration model
"""

from datetime import datetime
from . import db


class WorkConfig(db.Model):
    """User-specific work configuration settings"""
    id = db.Column(db.Integer, primary_key=True)
    work_hours_per_day = db.Column(db.Float, default=8.0)  # Default 8 hours
    mandatory_break_minutes = db.Column(db.Integer, default=30)  # Default 30 minutes
    break_threshold_hours = db.Column(db.Float, default=6.0)  # Work hours that trigger mandatory break
    additional_break_minutes = db.Column(db.Integer, default=15)  # Default 15 minutes for additional break
    additional_break_threshold_hours = db.Column(db.Float, default=9.0)  # Work hours that trigger additional break

    # Time rounding settings
    time_rounding_minutes = db.Column(db.Integer, default=0)  # 0 = no rounding, 15 = 15 min, 30 = 30 min
    round_to_nearest = db.Column(db.Boolean, default=True)  # True = round to nearest, False = round up

    # Date/time format settings
    time_format_24h = db.Column(db.Boolean, default=True)  # True = 24h, False = 12h (AM/PM)
    date_format = db.Column(db.String(20), default='ISO')  # ISO, US, EU, etc.

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f'<WorkConfig {self.id}: {self.work_hours_per_day}h/day, {self.mandatory_break_minutes}min break>'