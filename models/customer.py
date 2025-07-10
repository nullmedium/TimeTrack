"""
Customer-related models
"""

from datetime import datetime
from . import db


class Customer(db.Model):
    """Customer model for project assignment and invoicing"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)  # Customer code (e.g., CUST001)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Address information
    address_line1 = db.Column(db.String(255), nullable=True)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # Billing information
    billing_email = db.Column(db.String(120), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)
    payment_terms = db.Column(db.Integer, default=30)  # Days
    notes = db.Column(db.Text, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Company association for multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Foreign key to user who created the customer
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_customers')
    company = db.relationship('Company', backref='customers')
    projects = db.relationship('Project', back_populates='customer')
    
    # Unique constraint per company
    __table_args__ = (db.UniqueConstraint('company_id', 'code', name='uq_customer_code_per_company'),)
    
    def __repr__(self):
        return f'<Customer {self.name} ({self.code})>'