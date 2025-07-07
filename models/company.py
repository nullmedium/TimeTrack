"""
Company-related models
"""

from datetime import datetime
from . import db
from .enums import WorkRegion


class Company(db.Model):
    """Company model for multi-tenancy"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)  # URL-friendly identifier
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

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


class CompanySettings(db.Model):
    """Company-specific settings"""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), unique=True, nullable=False)
    
    # Work week settings
    work_week_start = db.Column(db.Integer, default=1)  # 1 = Monday, 7 = Sunday
    work_days = db.Column(db.String(20), default='1,2,3,4,5')  # Comma-separated day numbers
    
    # Time tracking settings
    allow_overlapping_entries = db.Column(db.Boolean, default=False)
    require_project_for_time_entry = db.Column(db.Boolean, default=True)
    allow_future_entries = db.Column(db.Boolean, default=False)
    max_hours_per_entry = db.Column(db.Float, default=24.0)
    
    # Feature toggles
    enable_tasks = db.Column(db.Boolean, default=True)
    enable_sprints = db.Column(db.Boolean, default=False)
    enable_client_access = db.Column(db.Boolean, default=False)
    
    # Notification settings
    notify_on_overtime = db.Column(db.Boolean, default=True)
    overtime_threshold_daily = db.Column(db.Float, default=8.0)
    overtime_threshold_weekly = db.Column(db.Float, default=40.0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship
    company = db.relationship('Company', backref=db.backref('settings', uselist=False))
    
    @classmethod
    def get_or_create(cls, company_id):
        """Get existing settings or create default ones"""
        settings = cls.query.filter_by(company_id=company_id).first()
        if not settings:
            settings = cls(company_id=company_id)
            db.session.add(settings)
            db.session.commit()
        return settings


class CompanyWorkConfig(db.Model):
    """Company-specific work configuration"""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Work hours configuration
    standard_hours_per_day = db.Column(db.Float, default=8.0)
    standard_hours_per_week = db.Column(db.Float, default=40.0)
    
    # Work region for compliance
    work_region = db.Column(db.Enum(WorkRegion), default=WorkRegion.OTHER)
    
    # Overtime rules
    overtime_enabled = db.Column(db.Boolean, default=True)
    overtime_rate = db.Column(db.Float, default=1.5)  # 1.5x regular rate
    double_time_enabled = db.Column(db.Boolean, default=False)
    double_time_threshold = db.Column(db.Float, default=12.0)  # Hours after which double time applies
    double_time_rate = db.Column(db.Float, default=2.0)
    
    # Break rules
    require_breaks = db.Column(db.Boolean, default=True)
    break_duration_minutes = db.Column(db.Integer, default=30)
    break_after_hours = db.Column(db.Float, default=6.0)
    
    # Weekly overtime rules
    weekly_overtime_threshold = db.Column(db.Float, default=40.0)
    weekly_overtime_rate = db.Column(db.Float, default=1.5)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    company = db.relationship('Company', backref='work_configs')
    
    def __repr__(self):
        return f'<CompanyWorkConfig {self.company.name if self.company else "Unknown"}: {self.work_region.value if self.work_region else "No region"}>'
    
    @classmethod
    def get_regional_preset(cls, region):
        """Get regional preset configuration."""
        presets = {
            WorkRegion.EU: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 40.0,
                'overtime_enabled': True,
                'overtime_rate': 1.5,
                'double_time_enabled': False,
                'double_time_threshold': 12.0,
                'double_time_rate': 2.0,
                'require_breaks': True,
                'break_duration_minutes': 30,
                'break_after_hours': 6.0,
                'weekly_overtime_threshold': 40.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'European Union'
            },
            WorkRegion.GERMANY: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 40.0,
                'overtime_enabled': True,
                'overtime_rate': 1.25,  # German overtime is typically 25% extra
                'double_time_enabled': False,
                'double_time_threshold': 10.0,
                'double_time_rate': 1.5,
                'require_breaks': True,
                'break_duration_minutes': 30,  # 30 min break after 6 hours
                'break_after_hours': 6.0,
                'weekly_overtime_threshold': 48.0,  # German law allows up to 48 hours/week
                'weekly_overtime_rate': 1.25,
                'region_name': 'Germany'
            },
            WorkRegion.USA: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 40.0,
                'overtime_enabled': True,
                'overtime_rate': 1.5,
                'double_time_enabled': False,
                'double_time_threshold': 12.0,
                'double_time_rate': 2.0,
                'require_breaks': False,  # No federal requirement
                'break_duration_minutes': 0,
                'break_after_hours': 999.0,  # Effectively disabled
                'weekly_overtime_threshold': 40.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'United States'
            },
            WorkRegion.UK: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 48.0,  # UK has 48-hour week limit
                'overtime_enabled': True,
                'overtime_rate': 1.5,
                'double_time_enabled': False,
                'double_time_threshold': 12.0,
                'double_time_rate': 2.0,
                'require_breaks': True,
                'break_duration_minutes': 20,
                'break_after_hours': 6.0,
                'weekly_overtime_threshold': 48.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'United Kingdom'
            },
            WorkRegion.CANADA: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 40.0,
                'overtime_enabled': True,
                'overtime_rate': 1.5,
                'double_time_enabled': False,
                'double_time_threshold': 12.0,
                'double_time_rate': 2.0,
                'require_breaks': True,
                'break_duration_minutes': 30,
                'break_after_hours': 5.0,
                'weekly_overtime_threshold': 40.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'Canada'
            },
            WorkRegion.AUSTRALIA: {
                'standard_hours_per_day': 7.6,  # 38-hour week / 5 days
                'standard_hours_per_week': 38.0,
                'overtime_enabled': True,
                'overtime_rate': 1.5,
                'double_time_enabled': True,
                'double_time_threshold': 10.0,
                'double_time_rate': 2.0,
                'require_breaks': True,
                'break_duration_minutes': 30,
                'break_after_hours': 5.0,
                'weekly_overtime_threshold': 38.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'Australia'
            },
            WorkRegion.OTHER: {
                'standard_hours_per_day': 8.0,
                'standard_hours_per_week': 40.0,
                'overtime_enabled': False,
                'overtime_rate': 1.5,
                'double_time_enabled': False,
                'double_time_threshold': 12.0,
                'double_time_rate': 2.0,
                'require_breaks': False,
                'break_duration_minutes': 0,
                'break_after_hours': 999.0,
                'weekly_overtime_threshold': 40.0,
                'weekly_overtime_rate': 1.5,
                'region_name': 'Other'
            }
        }
        
        return presets.get(region, presets[WorkRegion.OTHER])