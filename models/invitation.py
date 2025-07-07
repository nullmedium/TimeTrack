"""
Invitation model for company email invites
"""

from datetime import datetime, timedelta
from . import db
import secrets
import string


class CompanyInvitation(db.Model):
    """Company invitation model for email-based registration"""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(50), default='Team Member')  # Role to assign when accepted
    
    # Invitation metadata
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Status tracking
    accepted = db.Column(db.Boolean, default=False)
    accepted_at = db.Column(db.DateTime)
    accepted_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    company = db.relationship('Company', backref='invitations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_id], backref='sent_invitations')
    accepted_by = db.relationship('User', foreign_keys=[accepted_by_user_id], backref='accepted_invitation')
    
    def __init__(self, **kwargs):
        super(CompanyInvitation, self).__init__(**kwargs)
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(days=7)  # 7 days expiry
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def is_expired(self):
        """Check if invitation has expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self):
        """Check if invitation is valid (not accepted and not expired)"""
        return not self.accepted and not self.is_expired()
    
    def __repr__(self):
        return f'<CompanyInvitation {self.email} to {self.company.name}>'