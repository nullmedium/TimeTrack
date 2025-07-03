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
    
    # Project dates
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_projects')
    team = db.relationship('Team', backref='projects')
    time_entries = db.relationship('TimeEntry', backref='project', lazy=True)
    
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
    email = db.Column(db.String(120), nullable=False)
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
    
    def get_2fa_uri(self):
        """Get the provisioning URI for QR code generation"""
        if not self.two_factor_secret:
            return None
        import pyotp
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name="TimeTrack"
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