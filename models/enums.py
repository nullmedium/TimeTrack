"""
Enum definitions for the TimeTrack application
"""

import enum


class Role(enum.Enum):
    """User role enumeration"""
    TEAM_MEMBER = "Team Member"
    TEAM_LEADER = "Team Leader"
    SUPERVISOR = "Supervisor"
    ADMIN = "Administrator"  # Company-level admin
    SYSTEM_ADMIN = "System Administrator"  # System-wide admin


class AccountType(enum.Enum):
    """Account type for freelancer support"""
    COMPANY_USER = "Company User"
    FREELANCER = "Freelancer"


class WorkRegion(enum.Enum):
    """Work region enumeration for different labor law compliance"""
    USA = "United States"
    CANADA = "Canada"
    UK = "United Kingdom"
    GERMANY = "Germany"
    EU = "European Union"
    AUSTRALIA = "Australia"
    OTHER = "Other"


class CommentVisibility(enum.Enum):
    """Comment visibility levels"""
    PRIVATE = "Private"  # Only creator can see
    TEAM = "Team"       # Team members can see
    COMPANY = "Company" # All company users can see


class TaskStatus(enum.Enum):
    """Task status enumeration"""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    CANCELLED = "Cancelled"
    ARCHIVED = "Archived"


class TaskPriority(enum.Enum):
    """Task priority levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class SprintStatus(enum.Enum):
    """Sprint status enumeration"""
    PLANNING = "Planning"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class WidgetType(enum.Enum):
    """Dashboard widget types"""
    # Time Tracking Widgets
    CURRENT_TIMER = "current_timer"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_CHART = "weekly_chart"
    BREAK_REMINDER = "break_reminder"
    TIME_SUMMARY = "Time Summary"
    
    # Project Management Widgets
    ACTIVE_PROJECTS = "active_projects"
    PROJECT_PROGRESS = "project_progress"
    PROJECT_ACTIVITY = "project_activity"
    PROJECT_DEADLINES = "project_deadlines"
    PROJECT_STATUS = "Project Status"
    
    # Task Management Widgets
    ASSIGNED_TASKS = "assigned_tasks"
    TASK_PRIORITY = "task_priority"
    TASK_CALENDAR = "task_calendar"
    UPCOMING_TASKS = "upcoming_tasks"
    TASK_LIST = "Task List"
    
    # Sprint Widgets
    SPRINT_OVERVIEW = "sprint_overview"
    SPRINT_BURNDOWN = "sprint_burndown"
    SPRINT_PROGRESS = "Sprint Progress"
    
    # Team & Analytics Widgets
    TEAM_WORKLOAD = "team_workload"
    TEAM_PRESENCE = "team_presence"
    TEAM_ACTIVITY = "Team Activity"
    
    # Performance & Stats Widgets
    PRODUCTIVITY_STATS = "productivity_stats"
    TIME_DISTRIBUTION = "time_distribution"
    PERSONAL_STATS = "Personal Stats"
    
    # Action Widgets
    QUICK_ACTIONS = "quick_actions"
    RECENT_ACTIVITY = "recent_activity"


class WidgetSize(enum.Enum):
    """Dashboard widget sizes"""
    SMALL = "small"    # 1x1
    MEDIUM = "medium"  # 2x1
    LARGE = "large"    # 2x2
    WIDE = "wide"      # 3x1 or full width