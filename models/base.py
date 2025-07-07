"""
Base model utilities and mixins
"""

from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr
from . import db


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps"""
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class CompanyScopedMixin:
    """Mixin for models that belong to a company"""
    @declared_attr
    def company_id(cls):
        return db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)