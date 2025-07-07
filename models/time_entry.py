"""
Time entry model for tracking work hours
"""

from datetime import datetime
from . import db


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

    def __repr__(self):
        project_info = f" (Project: {self.project.code})" if self.project else ""
        return f'<TimeEntry {self.id}: {self.arrival_time} - {self.departure_time}{project_info}>'