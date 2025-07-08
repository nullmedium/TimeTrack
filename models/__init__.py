"""
Models package for TimeTrack application.
Split from monolithic models.py into domain-specific modules.
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import all models to maintain backward compatibility
from .enums import (
    Role, AccountType, WorkRegion, CommentVisibility, 
    TaskStatus, TaskPriority, SprintStatus, WidgetType, WidgetSize
)

from .company import Company, CompanySettings, CompanyWorkConfig
from .user import User, UserPreferences, UserDashboard
from .team import Team
from .project import Project, ProjectCategory
from .task import Task, TaskDependency, SubTask, Comment
from .time_entry import TimeEntry
from .sprint import Sprint
from .system import SystemSettings, BrandingSettings, SystemEvent
from .announcement import Announcement
from .dashboard import DashboardWidget, WidgetTemplate
from .work_config import WorkConfig
from .invitation import CompanyInvitation
from .note import Note, NoteVisibility, NoteLink, NoteFolder
from .note_share import NoteShare

# Make all models available at package level
__all__ = [
    'db',
    # Enums
    'Role', 'AccountType', 'WorkRegion', 'CommentVisibility',
    'TaskStatus', 'TaskPriority', 'SprintStatus', 'WidgetType', 'WidgetSize',
    # Models
    'Company', 'CompanySettings', 'CompanyWorkConfig',
    'User', 'UserPreferences', 'UserDashboard',
    'Team',
    'Project', 'ProjectCategory',
    'Task', 'TaskDependency', 'SubTask', 'Comment',
    'TimeEntry',
    'Sprint',
    'SystemSettings', 'BrandingSettings', 'SystemEvent',
    'Announcement',
    'DashboardWidget', 'WidgetTemplate',
    'WorkConfig',
    'CompanyInvitation',
    'Note', 'NoteVisibility', 'NoteLink', 'NoteFolder', 'NoteShare'
]