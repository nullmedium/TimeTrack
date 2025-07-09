"""
Alternative enum implementation using integers instead of PostgreSQL enums.
This avoids all PostgreSQL enum issues by using simple integers with Python-side validation.
"""

import enum

class IntEnum(enum.IntEnum):
    """Base class for integer-based enums."""
    
    @classmethod
    def choices(cls):
        """Return choices for forms."""
        return [(item.value, item.display_name) for item in cls]
    
    @property
    def display_name(self):
        """Get display name for the enum value."""
        return self._display_names.get(self, self.name.replace('_', ' ').title())


class TaskStatus(IntEnum):
    """Task status using integers."""
    TODO = 1
    IN_PROGRESS = 2
    IN_REVIEW = 3
    DONE = 4
    CANCELLED = 5
    ARCHIVED = 6
    
    _display_names = {
        TODO: "To Do",
        IN_PROGRESS: "In Progress",
        IN_REVIEW: "In Review", 
        DONE: "Done",
        CANCELLED: "Cancelled",
        ARCHIVED: "Archived"
    }


class TaskPriority(IntEnum):
    """Task priority using integers."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    
    _display_names = {
        LOW: "Low",
        MEDIUM: "Medium",
        HIGH: "High",
        URGENT: "Urgent"
    }


class Role(IntEnum):
    """User roles using integers."""
    TEAM_MEMBER = 1
    TEAM_LEADER = 2
    SUPERVISOR = 3
    ADMIN = 4
    SYSTEM_ADMIN = 5
    
    _display_names = {
        TEAM_MEMBER: "Team Member",
        TEAM_LEADER: "Team Leader",
        SUPERVISOR: "Supervisor",
        ADMIN: "Administrator",
        SYSTEM_ADMIN: "System Administrator"
    }


# Example model usage:
"""
from sqlalchemy import Integer, CheckConstraint
from models.enums_as_integers import TaskStatus, TaskPriority

class Task(db.Model):
    # Instead of: status = db.Column(db.Enum(TaskStatus))
    status = db.Column(db.Integer, default=TaskStatus.TODO)
    priority = db.Column(db.Integer, default=TaskPriority.MEDIUM)
    
    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in TaskStatus]),
            name='check_task_status'
        ),
        CheckConstraint(
            priority.in_([p.value for p in TaskPriority]),
            name='check_task_priority'
        ),
    )
    
    @property
    def status_display(self):
        return TaskStatus(self.status).display_name if self.status else None
    
    @property
    def priority_display(self):
        return TaskPriority(self.priority).display_name if self.priority else None
"""