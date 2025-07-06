from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import enum

db = SQLAlchemy()

# Define Role as an Enum for better type safety
class Role(enum.Enum):
    TEAM_MEMBER = "Team Member"
    TEAM_LEADER = "Team Leader"
    SUPERVISOR = "Supervisor"
    ADMIN = "Administrator"  # Company-level admin
    SYSTEM_ADMIN = "System Administrator"  # System-wide admin

# Define Account Type for freelancer support
class AccountType(enum.Enum):
    COMPANY_USER = "Company User"
    FREELANCER = "Freelancer"

# Company model for multi-tenancy
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)  # URL-friendly identifier
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Freelancer support
    is_personal = db.Column(db.Boolean, default=False)  # True for auto-created freelancer companies

    # Company settings
    is_active = db.Column(db.Boolean, default=True)
    max_users = db.Column(db.Integer, default=100)  # Optional user limit

    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    teams = db.relationship('Team', backref='company', lazy=True)
    projects = db.relationship('Project', backref='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.name}>'

    def generate_slug(self):
        """Generate URL-friendly slug from company name"""
        import re
        slug = re.sub(r'[^\w\s-]', '', self.name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

# Create Team model
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Company association for multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Relationship with users (one team has many users)
    users = db.relationship('User', backref='team', lazy=True)

    # Unique constraint per company
    __table_args__ = (db.UniqueConstraint('company_id', 'name', name='uq_team_name_per_company'),)

    def __repr__(self):
        return f'<Team {self.name}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    code = db.Column(db.String(20), nullable=False)  # Project code (e.g., PRJ001)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Company association for multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Foreign key to user who created the project (Admin/Supervisor)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Optional team assignment - if set, only team members can log time to this project
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

    # Project categorization
    category_id = db.Column(db.Integer, db.ForeignKey('project_category.id'), nullable=True)

    # Project dates
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_projects')
    team = db.relationship('Team', backref='projects')
    time_entries = db.relationship('TimeEntry', backref='project', lazy=True)
    category = db.relationship('ProjectCategory', back_populates='projects')

    # Unique constraint per company
    __table_args__ = (db.UniqueConstraint('company_id', 'code', name='uq_project_code_per_company'),)

    def __repr__(self):
        return f'<Project {self.code}: {self.name}>'

    def is_user_allowed(self, user):
        """Check if a user is allowed to log time to this project"""
        if not self.is_active:
            return False

        # Must be in same company
        if self.company_id != user.company_id:
            return False

        # Admins and Supervisors can log time to any project in their company
        if user.role in [Role.ADMIN, Role.SUPERVISOR]:
            return True

        # If project is team-specific, only team members can log time
        if self.team_id:
            return user.team_id == self.team_id

        # If no team restriction, any user in the company can log time
        return True

# Update User model to include role and team relationship
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Company association for multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Email verification fields
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    # New field for blocking users
    is_blocked = db.Column(db.Boolean, default=False)

    # New fields for role and team
    role = db.Column(db.Enum(Role, values_callable=lambda obj: [e.value for e in obj]), default=Role.TEAM_MEMBER)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

    # Freelancer support
    account_type = db.Column(db.Enum(AccountType, values_callable=lambda obj: [e.value for e in obj]), default=AccountType.COMPANY_USER)
    business_name = db.Column(db.String(100), nullable=True)  # Optional business name for freelancers

    # Unique constraints per company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'username', name='uq_user_username_per_company'),
        db.UniqueConstraint('company_id', 'email', name='uq_user_email_per_company'),
    )

    # Two-Factor Authentication fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)  # Base32 encoded secret
    
    # Avatar field
    avatar_url = db.Column(db.String(255), nullable=True)  # URL to user's avatar image

    # Relationships
    time_entries = db.relationship('TimeEntry', backref='user', lazy=True)
    work_config = db.relationship('WorkConfig', backref='user', lazy=True, uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        """Generate a verification token that expires in 24 hours"""
        self.verification_token = secrets.token_urlsafe(32)
        self.token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.verification_token

    def verify_token(self, token):
        """Verify the token and mark user as verified if valid"""
        if token == self.verification_token and self.token_expiry > datetime.utcnow():
            self.is_verified = True
            self.verification_token = None
            self.token_expiry = None
            return True
        return False

    def generate_2fa_secret(self):
        """Generate a new 2FA secret"""
        import pyotp
        self.two_factor_secret = pyotp.random_base32()
        return self.two_factor_secret
    
    def get_2fa_uri(self, issuer_name=None):
        """Get the provisioning URI for QR code generation"""
        if not self.two_factor_secret:
            return None
        import pyotp
        totp = pyotp.TOTP(self.two_factor_secret)
        if issuer_name is None:
            issuer_name = "Time Tracker"  # Default fallback
        return totp.provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )

    def verify_2fa_token(self, token, allow_setup=False):
        """Verify a 2FA token"""
        if not self.two_factor_secret:
            return False
        # During setup, allow verification even if 2FA isn't enabled yet
        if not allow_setup and not self.two_factor_enabled:
            return False
        import pyotp
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance

    def get_avatar_url(self, size=40):
        """Get user's avatar URL or generate a default one"""
        if self.avatar_url:
            return self.avatar_url
        
        # Generate a default avatar using DiceBear Avatars (similar to GitHub's identicons)
        # Using initials style for a clean, professional look
        import hashlib
        
        # Create a hash from username for consistent colors
        hash_input = f"{self.username}_{self.id}".encode('utf-8')
        hash_hex = hashlib.md5(hash_input).hexdigest()
        
        # Use DiceBear API for avatar generation
        # For initials style, we need to provide the actual initials
        initials = self.get_initials()
        
        # Generate avatar URL with initials
        # Using a color based on the hash for consistency
        bg_colors = ['0ea5e9', '8b5cf6', 'ec4899', 'f59e0b', '10b981', 'ef4444', '3b82f6', '6366f1']
        color_index = int(hash_hex[:2], 16) % len(bg_colors)
        bg_color = bg_colors[color_index]
        
        avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={initials}&size={size}&backgroundColor={bg_color}&fontSize=50"
        
        return avatar_url
    
    def get_initials(self):
        """Get user initials for avatar display"""
        parts = self.username.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif self.username:
            return self.username[:2].upper()
        return "??"

    def __repr__(self):
        return f'<User {self.username}>'

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'

class BrandingSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False, default='Time Tracker')
    logo_filename = db.Column(db.String(255), nullable=True)  # Filename of uploaded logo
    logo_alt_text = db.Column(db.String(255), nullable=True, default='Logo')
    favicon_filename = db.Column(db.String(255), nullable=True)  # Filename of uploaded favicon
    primary_color = db.Column(db.String(7), nullable=True, default='#007bff')  # Hex color
    
    # Imprint/Legal page settings
    imprint_enabled = db.Column(db.Boolean, default=False)  # Enable/disable imprint page
    imprint_title = db.Column(db.String(200), nullable=True, default='Imprint')  # Page title
    imprint_content = db.Column(db.Text, nullable=True)  # HTML content for imprint page
    
    # Meta fields
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    def __repr__(self):
        return f'<BrandingSettings {self.app_name}>'
    
    @staticmethod
    def get_current():
        """Get current branding settings or create defaults"""
        settings = BrandingSettings.query.first()
        if not settings:
            settings = BrandingSettings(
                app_name='Time Tracker',
                logo_alt_text='Application Logo'
            )
            db.session.add(settings)
            db.session.commit()
        return settings

class TimeEntry(db.Model):
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

class WorkConfig(db.Model):
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

# Define regional presets as an Enum
class WorkRegion(enum.Enum):
    GERMANY = "DE"
    UNITED_STATES = "US"
    UNITED_KINGDOM = "UK"
    FRANCE = "FR"
    EUROPEAN_UNION = "EU"
    CUSTOM = "CUSTOM"

# Company Work Configuration (Admin-only policies)
class CompanyWorkConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Work policy settings (legal requirements)
    work_hours_per_day = db.Column(db.Float, default=8.0)  # Standard work hours per day
    mandatory_break_minutes = db.Column(db.Integer, default=30)  # Required break duration
    break_threshold_hours = db.Column(db.Float, default=6.0)  # Hours that trigger mandatory break
    additional_break_minutes = db.Column(db.Integer, default=15)  # Additional break duration
    additional_break_threshold_hours = db.Column(db.Float, default=9.0)  # Hours that trigger additional break

    # Regional compliance
    region = db.Column(db.Enum(WorkRegion), default=WorkRegion.GERMANY)
    region_name = db.Column(db.String(50), default='Germany')

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    company = db.relationship('Company', backref='work_config')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    # Unique constraint - one config per company
    __table_args__ = (db.UniqueConstraint('company_id', name='uq_company_work_config'),)

    def __repr__(self):
        return f'<CompanyWorkConfig {self.company.name}: {self.region.value}, {self.work_hours_per_day}h/day>'

    @classmethod
    def get_regional_preset(cls, region):
        """Get regional preset configuration."""
        presets = {
            WorkRegion.GERMANY: {
                'work_hours_per_day': 8.0,
                'mandatory_break_minutes': 30,
                'break_threshold_hours': 6.0,
                'additional_break_minutes': 15,
                'additional_break_threshold_hours': 9.0,
                'region_name': 'Germany'
            },
            WorkRegion.UNITED_STATES: {
                'work_hours_per_day': 8.0,
                'mandatory_break_minutes': 0,  # No federal requirement
                'break_threshold_hours': 999.0,  # Effectively disabled
                'additional_break_minutes': 0,
                'additional_break_threshold_hours': 999.0,
                'region_name': 'United States'
            },
            WorkRegion.UNITED_KINGDOM: {
                'work_hours_per_day': 8.0,
                'mandatory_break_minutes': 20,
                'break_threshold_hours': 6.0,
                'additional_break_minutes': 0,
                'additional_break_threshold_hours': 999.0,
                'region_name': 'United Kingdom'
            },
            WorkRegion.FRANCE: {
                'work_hours_per_day': 7.0,  # 35-hour work week
                'mandatory_break_minutes': 20,
                'break_threshold_hours': 6.0,
                'additional_break_minutes': 0,
                'additional_break_threshold_hours': 999.0,
                'region_name': 'France'
            },
            WorkRegion.EUROPEAN_UNION: {
                'work_hours_per_day': 8.0,
                'mandatory_break_minutes': 20,
                'break_threshold_hours': 6.0,
                'additional_break_minutes': 0,
                'additional_break_threshold_hours': 999.0,
                'region_name': 'European Union (General)'
            }
        }
        return presets.get(region, presets[WorkRegion.GERMANY])

# Comment visibility enumeration
class CommentVisibility(enum.Enum):
    TEAM = "Team"  # Only visible to team members
    COMPANY = "Company"  # Visible to all company members

# Company Settings (General company preferences)
class CompanySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Comment settings
    default_comment_visibility = db.Column(db.Enum(CommentVisibility), default=CommentVisibility.COMPANY)
    allow_team_visibility_comments = db.Column(db.Boolean, default=True)  # Allow users to set comments as team-only
    
    # Task settings
    require_task_assignment = db.Column(db.Boolean, default=False)  # Tasks must be assigned before work can begin
    allow_task_creation_by_members = db.Column(db.Boolean, default=True)  # Team members can create tasks
    
    # Project settings
    restrict_project_access_by_team = db.Column(db.Boolean, default=False)  # Only team members can access team projects
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    company = db.relationship('Company', backref=db.backref('settings', uselist=False))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Unique constraint - one settings per company
    __table_args__ = (db.UniqueConstraint('company_id', name='uq_company_settings'),)
    
    def __repr__(self):
        return f'<CompanySettings {self.company.name}>'

# User Preferences (User-configurable display settings)
class UserPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Display format preferences
    time_format_24h = db.Column(db.Boolean, default=True)  # True = 24h, False = 12h (AM/PM)
    date_format = db.Column(db.String(20), default='ISO')  # ISO, US, EU, etc.

    # Time rounding preferences
    time_rounding_minutes = db.Column(db.Integer, default=0)  # 0 = no rounding, 15 = 15 min, 30 = 30 min
    round_to_nearest = db.Column(db.Boolean, default=True)  # True = round to nearest, False = round up

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))

    # Unique constraint - one preferences per user
    __table_args__ = (db.UniqueConstraint('user_id', name='uq_user_preferences'),)

    def __repr__(self):
        return f'<UserPreferences {self.user.username}: {self.date_format}, {"24h" if self.time_format_24h else "12h"}>'

# Project Category model for organizing projects
class ProjectCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#007bff')  # Hex color for UI
    icon = db.Column(db.String(50), nullable=True)  # Icon name/emoji

    # Company association for multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    company = db.relationship('Company', backref='project_categories')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    projects = db.relationship('Project', back_populates='category', lazy=True)

    # Unique constraint per company
    __table_args__ = (db.UniqueConstraint('company_id', 'name', name='uq_category_name_per_company'),)

    def __repr__(self):
        return f'<ProjectCategory {self.name}>'

# Task status enumeration
class TaskStatus(enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"
    CANCELLED = "Cancelled"

# Task priority enumeration
class TaskPriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

# Task model for project breakdown
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_number = db.Column(db.String(20), nullable=False, unique=True)  # e.g., "TSK-001", "TSK-002"
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Task properties
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    estimated_hours = db.Column(db.Float, nullable=True)  # Estimated time to complete

    # Project association
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # Sprint association (optional)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=True)

    # Task assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Task dates
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)
    archived_date = db.Column(db.Date, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    project = db.relationship('Project', backref='tasks')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tasks')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    subtasks = db.relationship('SubTask', backref='parent_task', lazy=True, cascade='all, delete-orphan')
    time_entries = db.relationship('TimeEntry', backref='task', lazy=True)

    def __repr__(self):
        return f'<Task {self.name} ({self.status.value})>'

    @property
    def progress_percentage(self):
        """Calculate task progress based on subtasks completion"""
        if not self.subtasks:
            return 100 if self.status == TaskStatus.COMPLETED else 0

        completed_subtasks = sum(1 for subtask in self.subtasks if subtask.status == TaskStatus.COMPLETED)
        return int((completed_subtasks / len(self.subtasks)) * 100)

    @property
    def total_time_logged(self):
        """Calculate total time logged to this task (in seconds)"""
        return sum(entry.duration or 0 for entry in self.time_entries if entry.duration)

    def can_user_access(self, user):
        """Check if a user can access this task"""
        return self.project.is_user_allowed(user)

    @classmethod
    def generate_task_number(cls, company_id):
        """Generate next task number for the company"""
        # Get the highest task number for this company
        last_task = cls.query.join(Project).filter(
            Project.company_id == company_id,
            cls.task_number.like('TSK-%')
        ).order_by(cls.task_number.desc()).first()
        
        if last_task and last_task.task_number:
            try:
                # Extract number from TSK-XXX format
                last_num = int(last_task.task_number.split('-')[1])
                return f"TSK-{last_num + 1:03d}"
            except (IndexError, ValueError):
                pass
        
        return "TSK-001"

    @property
    def blocked_by_tasks(self):
        """Get tasks that are blocking this task"""
        return [dep.blocking_task for dep in self.blocked_by_dependencies]
    
    @property
    def blocking_tasks(self):
        """Get tasks that this task is blocking"""
        return [dep.blocked_task for dep in self.blocking_dependencies]

# Task Dependencies model for tracking blocking relationships
class TaskDependency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # The task that is blocked (cannot start until blocking task is done)
    blocked_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # The task that is blocking (must be completed before blocked task can start)
    blocking_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # Dependency type (for future extension)
    dependency_type = db.Column(db.String(50), default='blocks', nullable=False)  # 'blocks', 'subtask', etc.
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    blocked_task = db.relationship('Task', foreign_keys=[blocked_task_id], 
                                 backref=db.backref('blocked_by_dependencies', cascade='all, delete-orphan'))
    blocking_task = db.relationship('Task', foreign_keys=[blocking_task_id], 
                                  backref=db.backref('blocking_dependencies', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Ensure a task doesn't block itself and prevent duplicate dependencies
    __table_args__ = (
        db.CheckConstraint('blocked_task_id != blocking_task_id', name='no_self_blocking'),
        db.UniqueConstraint('blocked_task_id', 'blocking_task_id', name='unique_dependency'),
    )
    
    def __repr__(self):
        return f'<TaskDependency {self.blocking_task_id} blocks {self.blocked_task_id}>'

# SubTask model for task breakdown
class SubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # SubTask properties
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    estimated_hours = db.Column(db.Float, nullable=True)

    # Parent task association
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)

    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Dates
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_subtasks')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    time_entries = db.relationship('TimeEntry', backref='subtask', lazy=True)

    def __repr__(self):
        return f'<SubTask {self.name} ({self.status.value})>'

    @property
    def total_time_logged(self):
        """Calculate total time logged to this subtask (in seconds)"""
        return sum(entry.duration or 0 for entry in self.time_entries if entry.duration)

    def can_user_access(self, user):
        """Check if a user can access this subtask"""
        return self.parent_task.can_user_access(user)

# Comment model for task discussions
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # Task association
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # Parent comment for thread support
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    
    # Visibility setting
    visibility = db.Column(db.Enum(CommentVisibility), default=CommentVisibility.COMPANY)
    
    # Edit tracking
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    task = db.relationship('Task', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='comments')
    replies = db.relationship('Comment', backref=db.backref('parent_comment', remote_side=[id]))
    
    def __repr__(self):
        return f'<Comment {self.id} on Task {self.task_id}>'
    
    def can_user_view(self, user):
        """Check if a user can view this comment based on visibility settings"""
        # First check if user can access the task
        if not self.task.can_user_access(user):
            return False
        
        # Then check visibility settings
        if self.visibility == CommentVisibility.TEAM:
            # Check if user is in the same team as the task's project
            if self.task.project.team_id:
                return user.team_id == self.task.project.team_id
            # If no team assigned to project, fall back to company visibility
            return user.company_id == self.task.project.company_id
        elif self.visibility == CommentVisibility.COMPANY:
            # Check if user is in the same company
            return user.company_id == self.task.project.company_id
        
        return False
    
    def can_user_edit(self, user):
        """Check if a user can edit this comment"""
        # Only the comment creator can edit their own comments
        return user.id == self.created_by_id
    
    def can_user_delete(self, user):
        """Check if a user can delete this comment"""
        # Comment creator can delete their own comments
        if user.id == self.created_by_id:
            return True
        
        # Admins and supervisors can delete any comment in their company
        if user.role in [Role.ADMIN, Role.SUPERVISOR]:
            return user.company_id == self.task.project.company_id
        
        return False

# Announcement model for system-wide announcements
class Announcement(db.Model):
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
            import json
            try:
                target_roles = json.loads(self.target_roles)
                if user.role.value not in target_roles:
                    return False
            except (json.JSONDecodeError, AttributeError):
                pass

        # Check company targeting
        if self.target_companies:
            import json
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

# System Event model for logging system activities
class SystemEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # e.g., 'login', 'logout', 'user_created', 'system_error'
    event_category = db.Column(db.String(30), nullable=False)  # e.g., 'auth', 'user_management', 'system', 'error'
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # 'info', 'warning', 'error', 'critical'
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Optional associations
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

    # Additional metadata (JSON string)
    event_metadata = db.Column(db.Text, nullable=True)  # Store additional event data as JSON

    # IP address and user agent for security tracking
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    user_agent = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship('User', backref='system_events')
    company = db.relationship('Company', backref='system_events')

    def __repr__(self):
        return f'<SystemEvent {self.event_type}: {self.description[:50]}>'

    @staticmethod
    def log_event(event_type, description, event_category='system', severity='info',
                  user_id=None, company_id=None, event_metadata=None, ip_address=None, user_agent=None):
        """Helper method to log system events"""
        event = SystemEvent(
            event_type=event_type,
            event_category=event_category,
            description=description,
            severity=severity,
            user_id=user_id,
            company_id=company_id,
            event_metadata=event_metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(event)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log to application logger if DB logging fails
            import logging
            logging.error(f"Failed to log system event: {e}")

    @staticmethod
    def get_recent_events(days=7, limit=100):
        """Get recent system events from the last N days"""
        from datetime import datetime, timedelta
        since = datetime.now() - timedelta(days=days)
        return SystemEvent.query.filter(
            SystemEvent.timestamp >= since
        ).order_by(SystemEvent.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_events_by_severity(severity, days=7, limit=50):
        """Get events by severity level"""
        from datetime import datetime, timedelta
        since = datetime.now() - timedelta(days=days)
        return SystemEvent.query.filter(
            SystemEvent.timestamp >= since,
            SystemEvent.severity == severity
        ).order_by(SystemEvent.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_system_health_summary():
        """Get a summary of system health based on recent events"""
        from datetime import datetime, timedelta
        from sqlalchemy import func

        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)

        # Count events by severity in last 24h
        recent_errors = SystemEvent.query.filter(
            SystemEvent.timestamp >= last_24h,
            SystemEvent.severity.in_(['error', 'critical'])
        ).count()

        recent_warnings = SystemEvent.query.filter(
            SystemEvent.timestamp >= last_24h,
            SystemEvent.severity == 'warning'
        ).count()

        # Count total events in last week
        weekly_events = SystemEvent.query.filter(
            SystemEvent.timestamp >= last_week
        ).count()

        # Get most recent error
        last_error = SystemEvent.query.filter(
            SystemEvent.severity.in_(['error', 'critical'])
        ).order_by(SystemEvent.timestamp.desc()).first()

        return {
            'errors_24h': recent_errors,
            'warnings_24h': recent_warnings,
            'total_events_week': weekly_events,
            'last_error': last_error,
            'health_status': 'healthy' if recent_errors == 0 else 'issues' if recent_errors < 5 else 'critical'
        }


# Sprint Management System
class SprintStatus(enum.Enum):
    PLANNING = "Planning"
    ACTIVE = "Active" 
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class Sprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Sprint status
    status = db.Column(db.Enum(SprintStatus), nullable=False, default=SprintStatus.PLANNING)
    
    # Company association - sprints are company-scoped
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Optional project association - can be project-specific or company-wide
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    
    # Sprint timeline
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Sprint goals and metrics
    goal = db.Column(db.Text, nullable=True)  # Sprint goal description
    capacity_hours = db.Column(db.Integer, nullable=True)  # Planned capacity in hours
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='sprints')
    project = db.relationship('Project', backref='sprints')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    tasks = db.relationship('Task', backref='sprint', lazy=True)
    
    def __repr__(self):
        return f'<Sprint {self.name}>'
    
    @property
    def is_current(self):
        """Check if this sprint is currently active"""
        from datetime import date
        today = date.today()
        return (self.status == SprintStatus.ACTIVE and 
                self.start_date <= today <= self.end_date)
    
    @property
    def duration_days(self):
        """Get sprint duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def days_remaining(self):
        """Get remaining days in sprint"""
        from datetime import date
        today = date.today()
        if self.end_date < today:
            return 0
        elif self.start_date > today:
            return self.duration_days
        else:
            return (self.end_date - today).days + 1
    
    @property
    def progress_percentage(self):
        """Calculate sprint progress percentage based on dates"""
        from datetime import date
        today = date.today()
        
        if today < self.start_date:
            return 0
        elif today > self.end_date:
            return 100
        else:
            total_days = self.duration_days
            elapsed_days = (today - self.start_date).days + 1
            return min(100, int((elapsed_days / total_days) * 100))
    
    def get_task_summary(self):
        """Get summary of tasks in this sprint"""
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])
        in_progress_tasks = len([t for t in self.tasks if t.status == TaskStatus.IN_PROGRESS])
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'in_progress': in_progress_tasks,
            'not_started': total_tasks - completed_tasks - in_progress_tasks,
            'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
        }
    
    def can_user_access(self, user):
        """Check if user can access this sprint"""
        # Must be in same company
        if self.company_id != user.company_id:
            return False
        
        # If sprint is project-specific, check project access
        if self.project_id:
            return self.project.is_user_allowed(user)
        
        # Company-wide sprints are accessible to all company members
        return True

# Dashboard Widget System
class WidgetType(enum.Enum):
    # Time Tracking Widgets
    CURRENT_TIMER = "current_timer"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_CHART = "weekly_chart"
    BREAK_REMINDER = "break_reminder"
    
    # Project Management Widgets
    ACTIVE_PROJECTS = "active_projects"
    PROJECT_PROGRESS = "project_progress"
    PROJECT_ACTIVITY = "project_activity"
    PROJECT_DEADLINES = "project_deadlines"
    
    # Task Management Widgets
    ASSIGNED_TASKS = "assigned_tasks"
    TASK_PRIORITY = "task_priority"
    TASK_TRENDS = "task_trends"
    
    # Analytics Widgets
    PRODUCTIVITY_METRICS = "productivity_metrics"
    TIME_DISTRIBUTION = "time_distribution"
    GOAL_PROGRESS = "goal_progress"
    PERFORMANCE_COMPARISON = "performance_comparison"
    
    # Team Widgets (Role-based)
    TEAM_OVERVIEW = "team_overview"
    RESOURCE_ALLOCATION = "resource_allocation"
    TEAM_PERFORMANCE = "team_performance"
    COMPANY_METRICS = "company_metrics"
    
    # Quick Action Widgets
    QUICK_TIMER = "quick_timer"
    FAVORITE_PROJECTS = "favorite_projects"
    RECENT_ACTIONS = "recent_actions"
    SHORTCUTS_PANEL = "shortcuts_panel"

class WidgetSize(enum.Enum):
    SMALL = "1x1"      # 1 grid unit
    MEDIUM = "2x1"     # 2 grid units wide, 1 high
    LARGE = "2x2"      # 2x2 grid units
    WIDE = "3x1"       # 3 grid units wide, 1 high
    TALL = "1x2"       # 1 grid unit wide, 2 high
    EXTRA_LARGE = "3x2" # 3x2 grid units

class UserDashboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), default='My Dashboard')
    is_default = db.Column(db.Boolean, default=True)
    layout_config = db.Column(db.Text)  # JSON string for grid layout configuration
    
    # Dashboard settings
    grid_columns = db.Column(db.Integer, default=6)  # Number of grid columns
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    auto_refresh = db.Column(db.Integer, default=300)  # Auto-refresh interval in seconds
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='dashboards')
    widgets = db.relationship('DashboardWidget', backref='dashboard', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint - one default dashboard per user
    __table_args__ = (db.Index('idx_user_default_dashboard', 'user_id', 'is_default'),)
    
    def __repr__(self):
        return f'<UserDashboard {self.name} (User: {self.user.username})>'

class DashboardWidget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('user_dashboard.id'), nullable=False)
    widget_type = db.Column(db.Enum(WidgetType), nullable=False)
    
    # Grid position and size
    grid_x = db.Column(db.Integer, nullable=False, default=0)  # X position in grid
    grid_y = db.Column(db.Integer, nullable=False, default=0)  # Y position in grid
    grid_width = db.Column(db.Integer, nullable=False, default=1)  # Width in grid units
    grid_height = db.Column(db.Integer, nullable=False, default=1)  # Height in grid units
    
    # Widget configuration
    title = db.Column(db.String(100))  # Custom widget title
    config = db.Column(db.Text)  # JSON string for widget-specific configuration
    refresh_interval = db.Column(db.Integer, default=60)  # Refresh interval in seconds
    
    # Widget state
    is_visible = db.Column(db.Boolean, default=True)
    is_minimized = db.Column(db.Boolean, default=False)
    z_index = db.Column(db.Integer, default=1)  # Stacking order
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<DashboardWidget {self.widget_type.value} ({self.grid_width}x{self.grid_height})>'
    
    @property
    def config_dict(self):
        """Parse widget configuration JSON"""
        if self.config:
            import json
            try:
                return json.loads(self.config)
            except:
                return {}
        return {}
    
    @config_dict.setter
    def config_dict(self, value):
        """Set widget configuration as JSON"""
        import json
        self.config = json.dumps(value) if value else None

class WidgetTemplate(db.Model):
    """Pre-defined widget templates for easy dashboard setup"""
    id = db.Column(db.Integer, primary_key=True)
    widget_type = db.Column(db.Enum(WidgetType), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icon name or emoji
    
    # Default configuration
    default_width = db.Column(db.Integer, default=1)
    default_height = db.Column(db.Integer, default=1)
    default_config = db.Column(db.Text)  # JSON string for default widget configuration
    
    # Access control
    required_role = db.Column(db.Enum(Role), default=Role.TEAM_MEMBER)
    is_active = db.Column(db.Boolean, default=True)
    
    # Categories for organization
    category = db.Column(db.String(50), default='General')  # Time, Projects, Tasks, Analytics, Team, Actions
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<WidgetTemplate {self.name} ({self.widget_type.value})>'
    
    def can_user_access(self, user):
        """Check if user has required role to use this widget"""
        if not self.is_active:
            return False
        
        # Define role hierarchy
        role_hierarchy = {
            Role.TEAM_MEMBER: 1,
            Role.TEAM_LEADER: 2,
            Role.SUPERVISOR: 3,
            Role.ADMIN: 4,
            Role.SYSTEM_ADMIN: 5
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(self.required_role, 0)
        
        return user_level >= required_level


# Note Sharing Visibility
class NoteVisibility(enum.Enum):
    PRIVATE = "Private"
    TEAM = "Team"
    COMPANY = "Company"


class Note(db.Model):
    """Markdown notes with sharing capabilities"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown content
    slug = db.Column(db.String(100), nullable=False)  # URL-friendly identifier
    
    # Visibility and sharing
    visibility = db.Column(db.Enum(NoteVisibility), nullable=False, default=NoteVisibility.PRIVATE)
    
    # Folder organization
    folder = db.Column(db.String(100), nullable=True)  # Folder path like "Work/Projects" or "Personal"
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Associations
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Optional associations
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # For team-specific notes
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)  # Link to project
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)  # Link to task
    
    # Tags for organization
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Pin important notes
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Soft delete
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='notes')
    company = db.relationship('Company', backref='notes')
    team = db.relationship('Team', backref='notes')
    project = db.relationship('Project', backref='notes')
    task = db.relationship('Task', backref='notes')
    
    # Unique constraint on slug per company
    __table_args__ = (db.UniqueConstraint('company_id', 'slug', name='uq_note_slug_per_company'),)
    
    def __repr__(self):
        return f'<Note {self.title}>'
    
    def generate_slug(self):
        """Generate URL-friendly slug from title"""
        import re
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', self.title.lower())
        # Replace spaces with hyphens
        slug = re.sub(r'[-\s]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Ensure uniqueness within company
        base_slug = slug
        counter = 1
        while Note.query.filter_by(company_id=self.company_id, slug=slug).filter(Note.id != self.id).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def can_user_view(self, user):
        """Check if user can view this note"""
        # Creator can always view
        if user.id == self.created_by_id:
            return True
        
        # Check company match
        if user.company_id != self.company_id:
            return False
        
        # Check visibility
        if self.visibility == NoteVisibility.COMPANY:
            return True
        elif self.visibility == NoteVisibility.TEAM:
            # Check if user is in the same team
            if self.team_id and user.team_id == self.team_id:
                return True
            # Admins can view all team notes
            if user.role in [Role.ADMIN, Role.SYSTEM_ADMIN]:
                return True
        
        return False
    
    def can_user_edit(self, user):
        """Check if user can edit this note"""
        # Creator can always edit
        if user.id == self.created_by_id:
            return True
        
        # Admins can edit company notes
        if user.role in [Role.ADMIN, Role.SYSTEM_ADMIN] and user.company_id == self.company_id:
            return True
        
        return False
    
    def get_tags_list(self):
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags_list(self, tags_list):
        """Set tags from a list"""
        self.tags = ','.join(tags_list) if tags_list else None
    
    def get_preview(self, length=200):
        """Get a plain text preview of the note content"""
        # Strip markdown formatting for preview
        import re
        from frontmatter_utils import parse_frontmatter
        
        # Extract body content without frontmatter
        _, body = parse_frontmatter(self.content)
        text = body
        
        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # Remove emphasis
        text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Clean up whitespace
        text = ' '.join(text.split())
        
        if len(text) > length:
            return text[:length] + '...'
        return text
    
    def render_html(self):
        """Render markdown content to HTML"""
        try:
            import markdown
            from frontmatter_utils import parse_frontmatter
            # Extract body content without frontmatter
            _, body = parse_frontmatter(self.content)
            # Use extensions for better markdown support
            html = markdown.markdown(body, extensions=['extra', 'codehilite', 'toc'])
            return html
        except ImportError:
            # Fallback if markdown not installed
            return f'<pre>{self.content}</pre>'
    
    def get_frontmatter(self):
        """Get frontmatter metadata from content"""
        from frontmatter_utils import parse_frontmatter
        metadata, _ = parse_frontmatter(self.content)
        return metadata
    
    def update_frontmatter(self):
        """Update content with current metadata as frontmatter"""
        from frontmatter_utils import update_frontmatter
        metadata = {
            'title': self.title,
            'visibility': self.visibility.value.lower(),
            'folder': self.folder,
            'tags': self.get_tags_list() if self.tags else None,
            'project': self.project.code if self.project else None,
            'task_id': self.task_id,
            'pinned': self.is_pinned if self.is_pinned else None,
            'created': self.created_at.isoformat() if self.created_at else None,
            'updated': self.updated_at.isoformat() if self.updated_at else None,
            'author': self.created_by.username if self.created_by else None
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        self.content = update_frontmatter(self.content, metadata)
    
    def sync_from_frontmatter(self):
        """Update model fields from frontmatter in content"""
        from frontmatter_utils import parse_frontmatter
        metadata, _ = parse_frontmatter(self.content)
        
        if metadata:
            # Update fields from frontmatter
            if 'title' in metadata:
                self.title = metadata['title']
            if 'visibility' in metadata:
                try:
                    self.visibility = NoteVisibility[metadata['visibility'].upper()]
                except KeyError:
                    pass
            if 'folder' in metadata:
                self.folder = metadata['folder']
            if 'tags' in metadata:
                if isinstance(metadata['tags'], list):
                    self.set_tags_list(metadata['tags'])
                elif isinstance(metadata['tags'], str):
                    self.tags = metadata['tags']
            if 'pinned' in metadata:
                self.is_pinned = bool(metadata['pinned'])


class NoteLink(db.Model):
    """Links between notes for creating relationships"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Source and target notes with cascade deletion
    source_note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    target_note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    
    # Link metadata
    link_type = db.Column(db.String(50), default='related')  # related, parent, child, etc.
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships with cascade deletion
    source_note = db.relationship('Note', foreign_keys=[source_note_id], 
                                backref=db.backref('outgoing_links', cascade='all, delete-orphan'))
    target_note = db.relationship('Note', foreign_keys=[target_note_id], 
                                backref=db.backref('incoming_links', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Unique constraint to prevent duplicate links
    __table_args__ = (db.UniqueConstraint('source_note_id', 'target_note_id', name='uq_note_link'),)
    
    def __repr__(self):
        return f'<NoteLink {self.source_note_id} -> {self.target_note_id}>'


class NoteFolder(db.Model):
    """Represents a folder for organizing notes"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Folder properties
    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(500), nullable=False)  # Full path like "Work/Projects/Q1"
    parent_path = db.Column(db.String(500), nullable=True)  # Parent folder path
    description = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    company = db.relationship('Company', foreign_keys=[company_id])
    
    # Unique constraint to prevent duplicate paths within a company
    __table_args__ = (db.UniqueConstraint('path', 'company_id', name='uq_folder_path_company'),)
    
    def __repr__(self):
        return f'<NoteFolder {self.path}>'