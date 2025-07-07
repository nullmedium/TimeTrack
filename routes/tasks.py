"""
Task Management Routes
Handles all task-related views and operations
"""

from flask import Blueprint, render_template, g, redirect, url_for, flash
from sqlalchemy import or_
from models import db, Role, Project, Task, User
from routes.auth import login_required, role_required, company_required

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def get_filtered_tasks_for_burndown(user, mode, start_date=None, end_date=None, project_filter=None):
    """Get filtered tasks for burndown chart"""
    from datetime import datetime, time
    
    # Base query - get tasks from user's company
    query = Task.query.join(Project).filter(Project.company_id == user.company_id)
    
    # Apply user/team filter
    if mode == 'personal':
        # For personal mode, get tasks assigned to the user or created by them
        query = query.filter(
            (Task.assigned_to_id == user.id) | 
            (Task.created_by_id == user.id)
        )
    elif mode == 'team' and user.team_id:
        # For team mode, get tasks from projects assigned to the team
        query = query.filter(Project.team_id == user.team_id)
    
    # Apply project filter
    if project_filter:
        if project_filter == 'none':
            # No project filter for tasks - they must belong to a project
            return []
        else:
            try:
                project_id = int(project_filter)
                query = query.filter(Task.project_id == project_id)
            except ValueError:
                pass
    
    # Apply date filters - use task creation date and completion date
    if start_date:
        query = query.filter(
            (Task.created_at >= datetime.combine(start_date, time.min)) |
            (Task.completed_date >= start_date)
        )
    if end_date:
        query = query.filter(
            Task.created_at <= datetime.combine(end_date, time.max)
        )
    
    return query.order_by(Task.created_at.desc()).all()


@tasks_bp.route('')
@role_required(Role.TEAM_MEMBER)
@company_required
def unified_task_management():
    """Unified task management interface"""
    
    # Get all projects the user has access to (for filtering and task creation)
    if g.user.role in [Role.ADMIN, Role.SUPERVISOR]:
        # Admins and Supervisors can see all company projects
        available_projects = Project.query.filter_by(
            company_id=g.user.company_id, 
            is_active=True
        ).order_by(Project.name).all()
    elif g.user.team_id:
        # Team members see team projects + unassigned projects
        available_projects = Project.query.filter(
            Project.company_id == g.user.company_id,
            Project.is_active == True,
            or_(Project.team_id == g.user.team_id, Project.team_id == None)
        ).order_by(Project.name).all()
        # Filter by actual access permissions
        available_projects = [p for p in available_projects if p.is_user_allowed(g.user)]
    else:
        # Unassigned users see only unassigned projects
        available_projects = Project.query.filter_by(
            company_id=g.user.company_id,
            team_id=None,
            is_active=True
        ).order_by(Project.name).all()
        available_projects = [p for p in available_projects if p.is_user_allowed(g.user)]
    
    # Get team members for task assignment (company-scoped)
    if g.user.role in [Role.ADMIN, Role.SUPERVISOR]:
        # Admins can assign to anyone in the company
        team_members = User.query.filter_by(
            company_id=g.user.company_id,
            is_blocked=False
        ).order_by(User.username).all()
    elif g.user.team_id:
        # Team members can assign to team members + supervisors/admins
        team_members = User.query.filter(
            User.company_id == g.user.company_id,
            User.is_blocked == False,
            or_(
                User.team_id == g.user.team_id,
                User.role.in_([Role.ADMIN, Role.SUPERVISOR])
            )
        ).order_by(User.username).all()
    else:
        # Unassigned users can assign to supervisors/admins only
        team_members = User.query.filter(
            User.company_id == g.user.company_id,
            User.is_blocked == False,
            User.role.in_([Role.ADMIN, Role.SUPERVISOR])
        ).order_by(User.username).all()
    
    # Convert team members to JSON-serializable format
    team_members_data = [{
        'id': member.id,
        'username': member.username,
        'email': member.email,
        'role': member.role.value if member.role else 'Team Member',
        'avatar_url': member.get_avatar_url(32)
    } for member in team_members]
    
    return render_template('unified_task_management.html',
                         title='Task Management',
                         available_projects=available_projects,
                         team_members=team_members_data)


