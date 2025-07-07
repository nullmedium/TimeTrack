"""
User management routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, abort
from models import db, User, Role, Team, TimeEntry, WorkConfig, UserPreferences, Project, Task, SubTask, ProjectCategory, UserDashboard, Comment, Company
from routes.auth import admin_required, company_required, login_required, system_admin_required
from flask_mail import Message
from flask import current_app
from utils.validation import FormValidator
from utils.repository import UserRepository
import logging

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/admin/users')


def get_available_roles():
    """Get roles available for user creation/editing based on current user's role"""
    current_user_role = g.user.role
    
    if current_user_role == Role.SYSTEM_ADMIN:
        # System admin can assign any role
        return [Role.TEAM_MEMBER, Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN, Role.SYSTEM_ADMIN]
    elif current_user_role == Role.ADMIN:
        # Admin can assign any role except system admin
        return [Role.TEAM_MEMBER, Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]
    elif current_user_role == Role.SUPERVISOR:
        # Supervisor can only assign team member and team leader roles
        return [Role.TEAM_MEMBER, Role.TEAM_LEADER]
    else:
        # Others cannot assign roles
        return []


@users_bp.route('')
@admin_required
@company_required
def admin_users():
    user_repo = UserRepository()
    users = user_repo.get_by_company(g.user.company_id)
    return render_template('admin_users.html', title='User Management', users=users)


@users_bp.route('/create', methods=['GET', 'POST'])
@admin_required
@company_required
def create_user():
    if request.method == 'POST':
        validator = FormValidator()
        user_repo = UserRepository()
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        auto_verify = 'auto_verify' in request.form

        # Get role and team
        role_name = request.form.get('role')
        team_id = request.form.get('team_id')

        # Validate required fields
        validator.validate_required(username, 'Username')
        validator.validate_required(email, 'Email')
        validator.validate_required(password, 'Password')
        
        # Validate uniqueness
        if validator.is_valid():
            validator.validate_unique(User, 'username', username, company_id=g.user.company_id)
            validator.validate_unique(User, 'email', email, company_id=g.user.company_id)

        if validator.is_valid():
            # Convert role string to enum
            try:
                role = Role[role_name] if role_name else Role.TEAM_MEMBER
            except KeyError:
                role = Role.TEAM_MEMBER

            # Create new user with role and team
            new_user = user_repo.create(
                username=username,
                email=email,
                company_id=g.user.company_id,
                is_verified=auto_verify,
                role=role,
                team_id=team_id if team_id else None
            )
            new_user.set_password(password)

            if not auto_verify:
                # Generate verification token and send email
                token = new_user.generate_verification_token()
                verification_url = url_for('verify_email', token=token, _external=True)

                try:
                    from flask_mail import Mail
                    mail = Mail(current_app)
                    
                    # Get branding for email
                    from models import BrandingSettings
                    branding = BrandingSettings.get_settings()
                    
                    msg = Message(
                        f'Welcome to {branding.app_name} - Verify Your Email',
                        sender=(branding.app_name, current_app.config['MAIL_USERNAME']),
                        recipients=[email]
                    )
                    msg.body = f'''Welcome to {branding.app_name}!

Your administrator has created an account for you. Please verify your email address to activate your account.

Username: {username}
Company: {g.company.name}

Click the link below to verify your email:
{verification_url}

This link will expire in 24 hours.

If you did not expect this email, please ignore it.

Best regards,
The {branding.app_name} Team
'''
                    mail.send(msg)
                    logger.info(f"Verification email sent to {email}")
                except Exception as e:
                    logger.error(f"Failed to send verification email: {str(e)}")
                    flash('User created but verification email could not be sent. Please contact the user directly.', 'warning')

            user_repo.save()

            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('users.admin_users'))

        validator.flash_errors()

    # Get all teams for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).all()
    roles = get_available_roles()

    return render_template('create_user.html', title='Create User', teams=teams, roles=roles)


@users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def edit_user(user_id):
    user_repo = UserRepository()
    user = user_repo.get_by_id_and_company(user_id, g.user.company_id)
    
    if not user:
        abort(404)

    if request.method == 'POST':
        validator = FormValidator()
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Get role and team
        role_name = request.form.get('role')
        team_id = request.form.get('team_id')

        # Validate required fields
        validator.validate_required(username, 'Username')
        validator.validate_required(email, 'Email')
        
        # Validate uniqueness (exclude current user)
        if validator.is_valid():
            if username != user.username:
                validator.validate_unique(User, 'username', username, company_id=g.user.company_id)
            if email != user.email:
                validator.validate_unique(User, 'email', email, company_id=g.user.company_id)
        
        if validator.is_valid():
            # Convert role string to enum
            try:
                role = Role[role_name] if role_name else Role.TEAM_MEMBER
            except KeyError:
                role = Role.TEAM_MEMBER

            user_repo.update(user,
                username=username,
                email=email,
                role=role,
                team_id=team_id if team_id else None
            )

            if password:
                user.set_password(password)

            user_repo.save()

            flash(f'User {username} updated successfully!', 'success')
            return redirect(url_for('users.admin_users'))

        validator.flash_errors()

    # Get all teams for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).all()
    roles = get_available_roles()

    return render_template('edit_user.html', title='Edit User', user=user, teams=teams, roles=roles)


@users_bp.route('/delete/<int:user_id>', methods=['POST'])
@admin_required
@company_required
def delete_user(user_id):
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()

    # Prevent deleting yourself
    if user.id == session.get('user_id'):
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('users.admin_users'))

    username = user.username
    
    try:
        # Check if user owns any critical resources
        owns_projects = Project.query.filter_by(created_by_id=user_id).count() > 0
        owns_tasks = Task.query.filter_by(created_by_id=user_id).count() > 0
        owns_subtasks = SubTask.query.filter_by(created_by_id=user_id).count() > 0
        
        needs_ownership_transfer = owns_projects or owns_tasks or owns_subtasks
        
        if needs_ownership_transfer:
            # Find an alternative admin/supervisor to transfer ownership to
            alternative_admin = User.query.filter(
                User.company_id == g.user.company_id,
                User.role.in_([Role.ADMIN, Role.SUPERVISOR]),
                User.id != user_id
            ).first()
            
            if alternative_admin:
                # Transfer ownership of projects to alternative admin
                if owns_projects:
                    Project.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
                
                # Transfer ownership of tasks to alternative admin
                if owns_tasks:
                    Task.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
                
                # Transfer ownership of subtasks to alternative admin
                if owns_subtasks:
                    SubTask.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
            else:
                # No alternative admin found but user owns resources
                flash('Cannot delete this user. They own resources but no other administrator or supervisor found to transfer ownership to.', 'error')
                return redirect(url_for('users.admin_users'))
        
        # Delete user-specific records that can be safely removed
        TimeEntry.query.filter_by(user_id=user_id).delete()
        WorkConfig.query.filter_by(user_id=user_id).delete()
        UserPreferences.query.filter_by(user_id=user_id).delete()
        
        # Delete user dashboards (cascades to widgets)
        UserDashboard.query.filter_by(user_id=user_id).delete()
        
        # Clear task and subtask assignments
        Task.query.filter_by(assigned_to_id=user_id).update({'assigned_to_id': None})
        SubTask.query.filter_by(assigned_to_id=user_id).update({'assigned_to_id': None})
        
        # Now safe to delete the user
        db.session.delete(user)
        db.session.commit()
        
        if needs_ownership_transfer and alternative_admin:
            flash(f'User {username} deleted successfully. Projects and tasks transferred to {alternative_admin.username}', 'success')
        else:
            flash(f'User {username} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('users.admin_users'))


@users_bp.route('/toggle-status/<int:user_id>', methods=['POST'])
@admin_required
@company_required
def toggle_user_status(user_id):
    """Toggle user active/blocked status"""
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()
    
    # Prevent blocking yourself
    if user.id == g.user.id:
        flash('You cannot block your own account', 'error')
        return redirect(url_for('users.admin_users'))
    
    # Toggle the blocked status
    user.is_blocked = not user.is_blocked
    db.session.commit()
    
    status = 'blocked' if user.is_blocked else 'unblocked'
    flash(f'User {user.username} has been {status}', 'success')
    
    return redirect(url_for('users.admin_users'))


# System Admin User Routes
@users_bp.route('/system-admin')
@system_admin_required
def system_admin_users():
    """System admin view of all users across all companies"""
    # Get filter parameters
    company_id = request.args.get('company_id', type=int)
    search_query = request.args.get('search', '')
    filter_type = request.args.get('filter', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query that returns tuples of (User, company_name)
    query = db.session.query(User, Company.name).join(Company)
    
    # Apply company filter
    if company_id:
        query = query.filter(User.company_id == company_id)
    
    # Apply search filter
    if search_query:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
    
    # Apply type filter
    if filter_type == 'system_admins':
        query = query.filter(User.role == Role.SYSTEM_ADMIN)
    elif filter_type == 'admins':
        query = query.filter(User.role == Role.ADMIN)
    elif filter_type == 'blocked':
        query = query.filter(User.is_blocked == True)
    elif filter_type == 'unverified':
        query = query.filter(User.is_verified == False)
    elif filter_type == 'freelancers':
        query = query.filter(Company.is_personal == True)
    
    # Order by company name and username
    query = query.order_by(Company.name, User.username)
    
    # Paginate the results
    try:
        users = query.paginate(page=page, per_page=per_page, error_out=False)
        # Debug log
        if users.items:
            logger.info(f"First item type: {type(users.items[0])}")
            logger.info(f"First item: {users.items[0]}")
    except Exception as e:
        logger.error(f"Error paginating users: {str(e)}")
        # Fallback to empty pagination
        from flask_sqlalchemy import Pagination
        users = Pagination(query=None, page=1, per_page=per_page, total=0, items=[])
    
    # Get all companies for filter dropdown
    companies = Company.query.order_by(Company.name).all()
    
    # Calculate statistics
    all_users = User.query.all()
    stats = {
        'total_users': len(all_users),
        'verified_users': len([u for u in all_users if u.is_verified]),
        'blocked_users': len([u for u in all_users if u.is_blocked]),
        'system_admins': len([u for u in all_users if u.role == Role.SYSTEM_ADMIN]),
        'company_admins': len([u for u in all_users if u.role == Role.ADMIN]),
    }
    
    return render_template('system_admin_users.html',
                         title='System User Management',
                         users=users,
                         companies=companies,
                         stats=stats,
                         selected_company_id=company_id,
                         search_query=search_query,
                         current_filter=filter_type)


@users_bp.route('/system-admin/<int:user_id>/edit', methods=['GET', 'POST'])
@system_admin_required
def system_admin_edit_user(user_id):
    """System admin edit any user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role')
        company_id = request.form.get('company_id', type=int)
        team_id = request.form.get('team_id', type=int)
        is_verified = 'is_verified' in request.form
        is_blocked = 'is_blocked' in request.form
        
        # Validate input
        validator = FormValidator()
        
        validator.validate_required(username, 'Username')
        validator.validate_required(email, 'Email')
        
        # Validate uniqueness (exclude current user)
        if validator.is_valid():
            if username != user.username:
                validator.validate_unique(User, 'username', username, company_id=user.company_id)
            if email != user.email:
                validator.validate_unique(User, 'email', email, company_id=user.company_id)
        
        # Prevent removing the last system admin
        if validator.is_valid() and user.role == Role.SYSTEM_ADMIN and role_name != 'SYSTEM_ADMIN':
            system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN, is_blocked=False).count()
            if system_admin_count <= 1:
                validator.errors.add('Cannot remove the last system administrator')
        
        if validator.is_valid():
            user.username = username
            user.email = email
            user.is_verified = is_verified
            user.is_blocked = is_blocked
            
            # Update company and team
            if company_id:
                user.company_id = company_id
            if team_id:
                user.team_id = team_id
            else:
                user.team_id = None  # Clear team if not selected
            
            # Update role
            try:
                user.role = Role[role_name] if role_name else Role.TEAM_MEMBER
            except KeyError:
                user.role = Role.TEAM_MEMBER
            
            if password:
                user.set_password(password)
            
            db.session.commit()
            flash(f'User {username} updated successfully!', 'success')
            return redirect(url_for('users.system_admin_users'))
        
        validator.flash_errors()
    
    # Get all companies and teams for the form
    companies = Company.query.order_by(Company.name).all()
    teams = Team.query.filter_by(company_id=user.company_id).order_by(Team.name).all()
    
    return render_template('system_admin_edit_user.html',
                         title='Edit User (System Admin)',
                         user=user,
                         companies=companies,
                         teams=teams,
                         roles=list(Role),
                         Role=Role)


@users_bp.route('/system-admin/<int:user_id>/delete', methods=['POST'])
@system_admin_required
def system_admin_delete_user(user_id):
    """System admin delete any user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == g.user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('users.system_admin_users'))
    
    # Prevent deleting the last system admin
    if user.role == Role.SYSTEM_ADMIN:
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()
        if system_admin_count <= 1:
            flash('Cannot delete the last system administrator', 'error')
            return redirect(url_for('users.system_admin_users'))
    
    username = user.username
    company_name = user.company.name
    
    try:
        # Check if this is the last admin/supervisor in the company
        admin_count = User.query.filter(
            User.company_id == user.company_id,
            User.role.in_([Role.ADMIN, Role.SUPERVISOR]),
            User.id != user_id
        ).count()
        
        if admin_count == 0:
            # This is the last admin - need to handle company data
            flash(f'User {username} is the last administrator in {company_name}. Company data will need to be handled.', 'warning')
            # For now, just prevent deletion
            return redirect(url_for('users.system_admin_users'))
        
        # Otherwise proceed with normal deletion
        # Delete user-specific records
        TimeEntry.query.filter_by(user_id=user_id).delete()
        WorkConfig.query.filter_by(user_id=user_id).delete()
        UserPreferences.query.filter_by(user_id=user_id).delete()
        UserDashboard.query.filter_by(user_id=user_id).delete()
        
        # Clear assignments
        Task.query.filter_by(assigned_to_id=user_id).update({'assigned_to_id': None})
        SubTask.query.filter_by(assigned_to_id=user_id).update({'assigned_to_id': None})
        
        # Transfer ownership of created items
        alternative_admin = User.query.filter(
            User.company_id == user.company_id,
            User.role.in_([Role.ADMIN, Role.SUPERVISOR]),
            User.id != user_id
        ).first()
        
        if alternative_admin:
            Project.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
            Task.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
            SubTask.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
            ProjectCategory.query.filter_by(created_by_id=user_id).update({'created_by_id': alternative_admin.id})
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {username} from {company_name} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('users.system_admin_users'))