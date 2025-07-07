"""
Project-related models
"""

from datetime import datetime
from . import db
from .enums import Role


class Project(db.Model):
    """Project model for time tracking"""
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

    # Project categorization
    category_id = db.Column(db.Integer, db.ForeignKey('project_category.id'), nullable=True)

    # Project dates
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_projects')
    team = db.relationship('Team', backref='projects')
    time_entries = db.relationship('TimeEntry', backref='project', lazy=True)
    category = db.relationship('ProjectCategory', back_populates='projects')

    # Unique constraint per company
    __table_args__ = (db.UniqueConstraint('company_id', 'code', name='uq_project_code_per_company'),)

    def __repr__(self):
        return f'<Project {self.name} ({self.code})>'

    def is_user_allowed(self, user):
        """Check if a user can log time to this project"""
        # User must be in the same company
        if user.company_id != self.company_id:
            return False

        # Admins and Supervisors can log time to any project in their company
        if user.role in [Role.ADMIN, Role.SUPERVISOR]:
            return True

        # If project is team-specific, only team members can log time
        if self.team_id:
            return user.team_id == self.team_id

        # If no team restriction, any user in the company can log time
        return True


class ProjectCategory(db.Model):
    """Project category for organization"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    color = db.Column(db.String(7), default='#3B82F6')  # Hex color for UI
    
    # Company association
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', back_populates='category')
    company = db.relationship('Company', backref='project_categories')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('company_id', 'name', name='uq_category_name_per_company'),)
    
    def __repr__(self):
        return f'<ProjectCategory {self.name}>'