"""
Task-related models
"""

from datetime import datetime
from . import db
from .enums import TaskStatus, TaskPriority, CommentVisibility, Role


class Task(db.Model):
    """Task model for project management"""
    id = db.Column(db.Integer, primary_key=True)
    task_number = db.Column(db.String(20), nullable=False, unique=True)  # e.g., "TSK-001", "TSK-002"
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Task properties
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.TODO)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    estimated_hours = db.Column(db.Float, nullable=True)  # Estimated time to complete

    # Project association
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # Sprint association (optional)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=True)

    # Task assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Task dates
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)
    archived_date = db.Column(db.Date, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    project = db.relationship('Project', backref='tasks')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tasks')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    subtasks = db.relationship('SubTask', backref='parent_task', lazy=True, cascade='all, delete-orphan')
    time_entries = db.relationship('TimeEntry', backref='task', lazy=True)

    def __repr__(self):
        return f'<Task {self.name} ({self.status.value})>'

    @property
    def progress_percentage(self):
        """Calculate task progress based on subtasks completion"""
        if not self.subtasks:
            return 100 if self.status == TaskStatus.DONE else 0

        completed_subtasks = sum(1 for subtask in self.subtasks if subtask.status == TaskStatus.DONE)
        return int((completed_subtasks / len(self.subtasks)) * 100)

    @property
    def total_time_logged(self):
        """Calculate total time logged to this task (in seconds)"""
        return sum(entry.duration or 0 for entry in self.time_entries if entry.duration)

    def can_user_access(self, user):
        """Check if a user can access this task"""
        return self.project.is_user_allowed(user)

    @classmethod
    def generate_task_number(cls, company_id):
        """Generate next task number for the company"""
        # Get the highest task number for this company
        last_task = cls.query.join(Project).filter(
            Project.company_id == company_id,
            cls.task_number.like('TSK-%')
        ).order_by(cls.task_number.desc()).first()
        
        if last_task and last_task.task_number:
            try:
                # Extract number from TSK-XXX format
                last_num = int(last_task.task_number.split('-')[1])
                return f"TSK-{last_num + 1:03d}"
            except (IndexError, ValueError):
                pass
        
        return "TSK-001"

    @property
    def blocked_by_tasks(self):
        """Get tasks that are blocking this task"""
        return [dep.blocking_task for dep in self.blocked_by_dependencies]
    
    @property
    def blocking_tasks(self):
        """Get tasks that this task is blocking"""
        return [dep.blocked_task for dep in self.blocking_dependencies]


class TaskDependency(db.Model):
    """Track dependencies between tasks"""
    id = db.Column(db.Integer, primary_key=True)
    
    # The task that is blocked (cannot start until blocking task is done)
    blocked_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # The task that is blocking (must be completed before blocked task can start)
    blocking_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # Dependency type (for future extension)
    dependency_type = db.Column(db.String(50), default='blocks', nullable=False)  # 'blocks', 'subtask', etc.
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    blocked_task = db.relationship('Task', foreign_keys=[blocked_task_id], 
                                 backref=db.backref('blocked_by_dependencies', cascade='all, delete-orphan'))
    blocking_task = db.relationship('Task', foreign_keys=[blocking_task_id], 
                                  backref=db.backref('blocking_dependencies', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Ensure a task doesn't block itself and prevent duplicate dependencies
    __table_args__ = (
        db.CheckConstraint('blocked_task_id != blocking_task_id', name='no_self_blocking'),
        db.UniqueConstraint('blocked_task_id', 'blocking_task_id', name='unique_dependency'),
    )
    
    def __repr__(self):
        return f'<TaskDependency {self.blocking_task_id} blocks {self.blocked_task_id}>'


class SubTask(db.Model):
    """Subtask model for breaking down tasks"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # SubTask properties
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.TODO)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    estimated_hours = db.Column(db.Float, nullable=True)

    # Parent task association
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)

    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Dates
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_subtasks')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    time_entries = db.relationship('TimeEntry', backref='subtask', lazy=True)

    def __repr__(self):
        return f'<SubTask {self.name} ({self.status.value})>'

    @property
    def total_time_logged(self):
        """Calculate total time logged to this subtask (in seconds)"""
        return sum(entry.duration or 0 for entry in self.time_entries if entry.duration)

    def can_user_access(self, user):
        """Check if a user can access this subtask"""
        return self.parent_task.can_user_access(user)


class Comment(db.Model):
    """Comment model for task discussions"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # Task association
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # Parent comment for thread support
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    
    # Visibility setting
    visibility = db.Column(db.Enum(CommentVisibility), default=CommentVisibility.COMPANY)
    
    # Edit tracking
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    task = db.relationship('Task', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='comments')
    replies = db.relationship('Comment', backref=db.backref('parent_comment', remote_side=[id]))
    
    def __repr__(self):
        return f'<Comment {self.id} on Task {self.task_id}>'
    
    def can_user_view(self, user):
        """Check if a user can view this comment based on visibility settings"""
        # First check if user can access the task
        if not self.task.can_user_access(user):
            return False
        
        # Check visibility rules
        if self.visibility == CommentVisibility.PRIVATE:
            return user.id == self.created_by_id
        elif self.visibility == CommentVisibility.TEAM:
            # User must be in the same team as the task's project
            if self.task.project.team_id:
                return user.team_id == self.task.project.team_id
            return True  # If no team restriction, all company users can see
        else:  # CommentVisibility.COMPANY
            return True  # All company users can see
    
    def can_user_edit(self, user):
        """Check if a user can edit this comment"""
        # Only the creator can edit their own comments
        return user.id == self.created_by_id
    
    def can_user_delete(self, user):
        """Check if a user can delete this comment"""
        # Creator can delete their own comments
        if user.id == self.created_by_id:
            return True
        
        # Admins can delete any comment in their company
        if user.role in [Role.ADMIN, Role.SYSTEM_ADMIN]:
            return True
        
        # Team leaders can delete comments on their team's tasks
        if user.role == Role.TEAM_LEADER and self.task.project.team_id == user.team_id:
            return True
        
        return False