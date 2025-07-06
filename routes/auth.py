# Standard library imports
from functools import wraps

# Third-party imports
from flask import flash, g, redirect, request, url_for

# Local application imports
from models import Company, Role, User


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def company_required(f):
    """
    Decorator to ensure user has a valid company association and set company context.
    """
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
            flash('Your company account is inactive.', 'error')
            return redirect(url_for('home'))

        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user.role not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role not in [Role.ADMIN, Role.SYSTEM_ADMIN]:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def system_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role != Role.SYSTEM_ADMIN:
            flash('System admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function