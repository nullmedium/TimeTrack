"""
Sprint Management Routes
Handles all sprint-related views
"""

from flask import Blueprint, render_template, g, redirect, url_for, flash
from sqlalchemy import or_
from models import db, Role, Project, Sprint
from routes.auth import login_required, role_required, company_required

sprints_bp = Blueprint('sprints', __name__, url_prefix='/sprints')


@sprints_bp.route('')
@role_required(Role.TEAM_MEMBER)
@company_required
def sprint_management():
    """Sprint management interface"""
    
    # Get all projects the user has access to (for sprint assignment)
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
    
    return render_template('sprint_management.html',
                         title='Sprint Management',
                         available_projects=available_projects)