"""
Report models for the Advanced Report Engine.
"""

from datetime import datetime
from . import db


class ReportTemplate(db.Model):
    """System and user-defined report templates."""
    __tablename__ = 'report_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), default='custom')
    template_config = db.Column(db.JSON, nullable=False, default=dict)
    thumbnail = db.Column(db.Text)
    is_system = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', ondelete='CASCADE'))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    company = db.relationship('Company')
    saved_reports = db.relationship('SavedReport', back_populates='template')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'template_config': self.template_config,
            'thumbnail': self.thumbnail,
            'is_system': self.is_system,
            'is_public': self.is_public,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SavedReport(db.Model):
    """User-saved report configurations."""
    __tablename__ = 'saved_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id', ondelete='SET NULL'))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    config = db.Column(db.JSON, nullable=False, default=dict)
    filters = db.Column(db.JSON, default=dict)
    is_favorite = db.Column(db.Boolean, default=False)
    last_accessed = db.Column(db.TIMESTAMP)
    access_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Relationships
    user = db.relationship('User')
    template = db.relationship('ReportTemplate', back_populates='saved_reports')
    shares = db.relationship('ReportShare', back_populates='report', cascade='all, delete-orphan')
    export_history = db.relationship('ReportExportHistory', back_populates='report', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'template_name': self.template.name if self.template else None,
            'name': self.name,
            'description': self.description,
            'config': self.config,
            'filters': self.filters,
            'is_favorite': self.is_favorite,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'access_count': self.access_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_shared': len(self.shares) > 0
        }
    
    def update_access(self):
        """Update last accessed timestamp and increment counter."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class ReportComponent(db.Model):
    """Reusable report components (charts, tables, metrics)."""
    __tablename__ = 'report_components'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'chart', 'table', 'metric', 'text'
    component_config = db.Column(db.JSON, nullable=False, default=dict)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'component_config': self.component_config,
            'is_system': self.is_system
        }


class ReportShare(db.Model):
    """Report sharing permissions."""
    __tablename__ = 'report_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('saved_reports.id', ondelete='CASCADE'), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    shared_with_team_id = db.Column(db.Integer, db.ForeignKey('team.id', ondelete='CASCADE'))
    permission = db.Column(db.String(20), default='view')  # 'view', 'edit'
    shared_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    expires_at = db.Column(db.TIMESTAMP)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    # Relationships
    report = db.relationship('SavedReport', back_populates='shares')
    user = db.relationship('User', foreign_keys=[shared_with_user_id])
    team = db.relationship('Team', foreign_keys=[shared_with_team_id])
    sharer = db.relationship('User', foreign_keys=[shared_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'shared_with': {
                'user_id': self.shared_with_user_id,
                'user_name': self.user.username if self.user else None,
                'team_id': self.shared_with_team_id,
                'team_name': self.team.name if self.team else None
            },
            'permission': self.permission,
            'shared_by': self.sharer.username if self.sharer else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def is_expired(self):
        """Check if the share has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class ReportExportHistory(db.Model):
    """Track report export history for analytics."""
    __tablename__ = 'report_export_history'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('saved_reports.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    export_format = db.Column(db.String(20), nullable=False)  # 'pdf', 'excel', 'csv', 'png'
    file_size = db.Column(db.Integer)
    duration_ms = db.Column(db.Integer)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    # Relationships
    report = db.relationship('SavedReport', back_populates='export_history')
    user = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'report_name': self.report.name if self.report else None,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'export_format': self.export_format,
            'file_size': self.file_size,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }