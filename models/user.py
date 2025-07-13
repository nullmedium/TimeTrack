"""
User-related models
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from . import db
from .enums import Role, AccountType, WidgetType, WidgetSize


class User(db.Model):
    """User model with multi-tenancy and role-based access"""
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
    
    # Password reset fields
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True)
    password_reset_expiry = db.Column(db.DateTime, nullable=True)

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
    
    def generate_password_reset_token(self):
        """Generate a password reset token"""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        return token
    
    def verify_password_reset_token(self, token):
        """Verify if the password reset token is valid"""
        if not self.password_reset_token or self.password_reset_token != token:
            return False
        if not self.password_reset_expiry or datetime.utcnow() > self.password_reset_expiry:
            return False
        return True
    
    def clear_password_reset_token(self):
        """Clear the password reset token after use"""
        self.password_reset_token = None
        self.password_reset_expiry = None
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'


class UserPreferences(db.Model):
    """User preferences and settings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # UI preferences
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(20), default='ISO')  # ISO, US, German, etc.
    time_format = db.Column(db.String(10), default='24h')
    time_format_24h = db.Column(db.Boolean, default=True)  # True for 24h, False for 12h
    
    # Time tracking preferences
    time_rounding_minutes = db.Column(db.Integer, default=0)  # 0, 5, 10, 15, 30, 60
    round_to_nearest = db.Column(db.Boolean, default=False)  # False=round down, True=round to nearest
    timer_reminder_enabled = db.Column(db.Boolean, default=True)
    timer_reminder_interval = db.Column(db.Integer, default=60)  # Minutes
    
    # Dashboard preferences
    dashboard_layout = db.Column(db.JSON, nullable=True)  # Store custom dashboard layout
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))


class UserDashboard(db.Model):
    """User's dashboard configuration"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), default='My Dashboard')
    is_default = db.Column(db.Boolean, default=True)
    layout_config = db.Column(db.Text)  # JSON string for grid layout configuration
    
    # Dashboard settings
    grid_columns = db.Column(db.Integer, default=6)  # Number of grid columns
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    auto_refresh = db.Column(db.Integer, default=300)  # Auto-refresh interval in seconds
    
    # Additional configuration (from new model)
    layout = db.Column(db.JSON, nullable=True)  # Grid layout configuration (alternative format)
    is_locked = db.Column(db.Boolean, default=False)  # Prevent accidental changes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('dashboards', lazy='dynamic'))
    widgets = db.relationship('DashboardWidget', backref='dashboard', lazy=True, cascade='all, delete')