from datetime import datetime, timedelta
from . import db
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash


class NoteShare(db.Model):
    """Public sharing links for notes"""
    __tablename__ = 'note_share'
    
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Share settings
    expires_at = db.Column(db.DateTime, nullable=True)  # None means no expiry
    password_hash = db.Column(db.String(255), nullable=True)  # Optional password protection
    view_count = db.Column(db.Integer, default=0)
    max_views = db.Column(db.Integer, nullable=True)  # Limit number of views
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    note = db.relationship('Note', backref=db.backref('shares', cascade='all, delete-orphan', lazy='dynamic'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __init__(self, **kwargs):
        super(NoteShare, self).__init__(**kwargs)
        if not self.token:
            self.token = self.generate_token()
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def set_password(self, password):
        """Set password protection for the share"""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None
    
    def check_password(self, password):
        """Check if the provided password is correct"""
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)
    
    def is_valid(self):
        """Check if share link is still valid"""
        # Check expiration
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        
        # Check view count
        if self.max_views and self.view_count >= self.max_views:
            return False
        
        return True
    
    def is_expired(self):
        """Check if the share has expired"""
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False
    
    def is_view_limit_reached(self):
        """Check if view limit has been reached"""
        if self.max_views and self.view_count >= self.max_views:
            return True
        return False
    
    def record_access(self):
        """Record that the share was accessed"""
        self.view_count += 1
        self.last_accessed_at = datetime.now()
    
    def get_share_url(self, _external=True):
        """Get the full URL for this share"""
        from flask import url_for
        return url_for('notes_public.view_shared_note', 
                      token=self.token, 
                      _external=_external)
    
    def to_dict(self):
        """Convert share to dictionary for API responses"""
        return {
            'id': self.id,
            'token': self.token,
            'url': self.get_share_url(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'has_password': bool(self.password_hash),
            'max_views': self.max_views,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by.username,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'is_valid': self.is_valid(),
            'is_expired': self.is_expired(),
            'is_view_limit_reached': self.is_view_limit_reached()
        }