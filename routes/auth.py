"""
Authentication decorators for route protection
"""

from functools import wraps
from flask import g, redirect, url_for, flash, request
from models import Role, Company

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(min_role):
    """Decorator to require a minimum role for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                return redirect(url_for('login', next=request.url))
            
            # Admin and System Admin always have access
            if g.user.role == Role.ADMIN or g.user.role == Role.SYSTEM_ADMIN:
                return f(*args, **kwargs)
            
            # Define role hierarchy
            role_hierarchy = {
                Role.TEAM_MEMBER: 1,
                Role.TEAM_LEADER: 2,
                Role.SUPERVISOR: 3,
                Role.ADMIN: 4,
                Role.SYSTEM_ADMIN: 5
            }
            
            user_role_value = role_hierarchy.get(g.user.role, 0)
            min_role_value = role_hierarchy.get(min_role, 0)
            
            if user_role_value < min_role_value:
                flash('You do not have sufficient permissions to access this page.', 'error')
                return redirect(url_for('home'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def company_required(f):
    """Decorator to ensure user has a valid company association and set company context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        
        # System admins can access without company association
        if g.user.role == Role.SYSTEM_ADMIN:
            return f(*args, **kwargs)
        
        if g.user.company_id is None:
            flash('You must be associated with a company to access this page.', 'error')
            return redirect(url_for('setup_company'))
        
        # Set company context
        g.company = Company.query.get(g.user.company_id)
        if not g.company or not g.company.is_active:
            flash('Your company is not active. Please contact support.', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        if g.user.role not in [Role.ADMIN, Role.SYSTEM_ADMIN]:
            flash('You must be an administrator to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


def system_admin_required(f):
    """Decorator to require system admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        if g.user.role != Role.SYSTEM_ADMIN:
            flash('You must be a system administrator to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function