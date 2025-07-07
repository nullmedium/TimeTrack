"""
Team model
"""

from datetime import datetime
from . import db


class Team(db.Model):
    """Team model for organizing users"""
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