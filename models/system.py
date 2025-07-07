"""
System-related models
"""

from datetime import datetime, timedelta
from . import db


class SystemSettings(db.Model):
    """Key-value store for system-wide settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'


class BrandingSettings(db.Model):
    """Branding and customization settings"""
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
    def get_settings():
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
    
    @staticmethod
    def get_current():
        """Alias for get_settings() for backward compatibility"""
        return BrandingSettings.get_settings()


class SystemEvent(db.Model):
    """System event logging for audit and monitoring"""
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
        since = datetime.now() - timedelta(days=days)
        return SystemEvent.query.filter(
            SystemEvent.timestamp >= since
        ).order_by(SystemEvent.timestamp.desc()).limit(limit).all()

    @staticmethod
    def cleanup_old_events(days=90):
        """Delete system events older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = SystemEvent.query.filter(
            SystemEvent.timestamp < cutoff_date
        ).delete()
        db.session.commit()
        return deleted_count