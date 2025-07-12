"""
Time entry model for tracking work hours
"""

from datetime import datetime
from . import db
from .enums import BillingType


class TimeEntry(db.Model):
    """Time entry model for tracking work hours"""
    id = db.Column(db.Integer, primary_key=True)
    arrival_time = db.Column(db.DateTime, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    is_paused = db.Column(db.Boolean, default=False)
    pause_start_time = db.Column(db.DateTime, nullable=True)
    total_break_duration = db.Column(db.Integer, default=0)  # Total break duration in seconds
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Project association - nullable for backward compatibility
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    # Task/SubTask associations - nullable for backward compatibility
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    subtask_id = db.Column(db.Integer, db.ForeignKey('sub_task.id'), nullable=True)

    # Optional notes/description for the time entry
    notes = db.Column(db.Text, nullable=True)

    # Billing override fields
    is_billable = db.Column(db.Boolean, nullable=True)  # None = inherit from project
    billing_rate = db.Column(db.Numeric(10, 2), nullable=True)  # Override project rate
    billing_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Calculated amount

    def __repr__(self):
        project_info = f" (Project: {self.project.code})" if self.project else ""
        return f'<TimeEntry {self.id}: {self.arrival_time} - {self.departure_time}{project_info}>'

    @property
    def effective_is_billable(self):
        """Get the effective billable status (considering project default)"""
        if self.is_billable is not None:
            return self.is_billable
        if self.project:
            return self.project.billing_type != BillingType.NON_BILLABLE
        return False

    @property
    def effective_billing_rate(self):
        """Get the effective billing rate (considering project default)"""
        if self.billing_rate is not None:
            return float(self.billing_rate)
        if self.project:
            if self.project.billing_type == BillingType.HOURLY and self.project.hourly_rate:
                return float(self.project.hourly_rate)
            elif self.project.billing_type == BillingType.DAILY_RATE and self.project.daily_rate:
                # For daily rate, we'll return the daily rate divided by standard hours
                # This will be used differently in calculate_billing_amount
                return float(self.project.daily_rate)
        return 0.0

    def calculate_billing_amount(self):
        """Calculate the billing amount for this time entry"""
        if not self.effective_is_billable or not self.duration:
            return 0.0
        
        hours = self.duration / 3600.0  # Convert seconds to hours
        
        if self.project and self.project.billing_type == BillingType.DAILY_RATE:
            # For daily rate, calculate based on the portion of the day worked
            # Assuming 8 hours is a standard work day
            standard_hours_per_day = 8.0
            days_worked = hours / standard_hours_per_day
            daily_rate = float(self.project.daily_rate) if self.project.daily_rate else 0
            return round(days_worked * daily_rate, 2)
        else:
            # For hourly rate or custom rate
            rate = self.effective_billing_rate
            return round(hours * rate, 2)