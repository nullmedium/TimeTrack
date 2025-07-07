"""
Sprint model for agile project management
"""

from datetime import datetime, date
from . import db
from .enums import SprintStatus, TaskStatus, Role


class Sprint(db.Model):
    """Sprint model for agile project management"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Sprint status
    status = db.Column(db.Enum(SprintStatus), nullable=False, default=SprintStatus.PLANNING)
    
    # Company association - sprints are company-scoped
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Optional project association - can be project-specific or company-wide
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    
    # Sprint timeline
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Sprint goals and metrics
    goal = db.Column(db.Text, nullable=True)  # Sprint goal description
    capacity_hours = db.Column(db.Integer, nullable=True)  # Planned capacity in hours
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='sprints')
    project = db.relationship('Project', backref='sprints')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    tasks = db.relationship('Task', backref='sprint', lazy=True)
    
    def __repr__(self):
        return f'<Sprint {self.name}>'
    
    @property
    def is_current(self):
        """Check if this sprint is currently active"""
        today = date.today()
        return (self.status == SprintStatus.ACTIVE and 
                self.start_date <= today <= self.end_date)
    
    @property
    def duration_days(self):
        """Get sprint duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def days_remaining(self):
        """Get remaining days in sprint"""
        today = date.today()
        if self.end_date < today:
            return 0
        elif self.start_date > today:
            return self.duration_days
        else:
            return (self.end_date - today).days + 1
    
    @property
    def progress_percentage(self):
        """Calculate sprint progress percentage based on dates"""
        today = date.today()
        
        if today < self.start_date:
            return 0
        elif today > self.end_date:
            return 100
        else:
            total_days = self.duration_days
            elapsed_days = (today - self.start_date).days + 1
            return min(100, int((elapsed_days / total_days) * 100))
    
    def get_task_summary(self):
        """Get summary of tasks in this sprint"""
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks if t.status == TaskStatus.DONE])
        in_progress_tasks = len([t for t in self.tasks if t.status == TaskStatus.IN_PROGRESS])
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'in_progress': in_progress_tasks,
            'not_started': total_tasks - completed_tasks - in_progress_tasks,
            'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
        }
    
    def can_user_access(self, user):
        """Check if user can access this sprint"""
        # Must be in same company
        if self.company_id != user.company_id:
            return False
        
        # If sprint is project-specific, check project access
        if self.project_id:
            return self.project.is_user_allowed(user)
        
        # Company-wide sprints can be accessed by all company users
        return True
    
    def can_user_modify(self, user):
        """Check if user can modify this sprint"""
        if not self.can_user_access(user):
            return False
        
        # Only admins and supervisors can modify sprints
        return user.role in [Role.ADMIN, Role.SUPERVISOR]