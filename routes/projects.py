"""
Project Management Routes
Handles all project-related views and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from datetime import datetime
from models import db, Project, Team, ProjectCategory, TimeEntry, Role, Task, User, CompanySettings
from models.enums import BillingType
from routes.auth import role_required, company_required, admin_required
from utils.validation import FormValidator
from utils.repository import ProjectRepository
from utils.currency import get_currency_symbol

projects_bp = Blueprint('projects', __name__, url_prefix='/admin/projects')


@projects_bp.route('')
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage projects
@company_required
def admin_projects():
    project_repo = ProjectRepository()
    projects = project_repo.get_by_company_ordered(g.user.company_id, Project.created_at.desc())
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()
    
    # Get company currency
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    currency_symbol = get_currency_symbol(currency)
    
    return render_template('admin_projects.html', 
                         title='Project Management', 
                         projects=projects, 
                         categories=categories,
                         currency=currency,
                         currency_symbol=currency_symbol)


@projects_bp.route('/create', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def create_project():
    if request.method == 'POST':
        validator = FormValidator()
        project_repo = ProjectRepository()
        
        name = request.form.get('name')
        description = request.form.get('description')
        code = request.form.get('code')
        team_id = request.form.get('team_id') or None
        category_id = request.form.get('category_id') or None
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Billing fields
        billing_type = request.form.get('billing_type', 'NON_BILLABLE')
        if not billing_type:
            billing_type = 'NON_BILLABLE'
        hourly_rate = request.form.get('hourly_rate')
        billing_notes = request.form.get('billing_notes')

        # Validate required fields
        validator.validate_required(name, 'Project name')
        validator.validate_required(code, 'Project code')
        
        # Validate code uniqueness
        if validator.is_valid():
            validator.validate_unique(Project, 'code', code, company_id=g.user.company_id)
        
        # Validate billing fields
        try:
            # Validate billing type is a valid enum
            billing_type_enum = BillingType[billing_type]
        except KeyError:
            validator.add_error(f'Invalid billing type: {billing_type}')
            billing_type_enum = BillingType.NON_BILLABLE
        
        if billing_type == 'HOURLY' and not hourly_rate:
            validator.add_error('Hourly rate is required for hourly billing')
        
        if hourly_rate:
            try:
                hourly_rate = float(hourly_rate)
                if hourly_rate < 0:
                    validator.add_error('Hourly rate must be positive')
            except ValueError:
                validator.add_error('Invalid hourly rate')

        # Parse dates
        start_date = validator.parse_date(start_date_str, 'Start date')
        end_date = validator.parse_date(end_date_str, 'End date')
        
        # Validate date range
        if start_date and end_date:
            validator.validate_date_range(start_date, end_date)

        if validator.is_valid():
            project = project_repo.create(
                name=name,
                description=description,
                code=code.upper(),
                company_id=g.user.company_id,
                team_id=int(team_id) if team_id else None,
                category_id=int(category_id) if category_id else None,
                start_date=start_date,
                end_date=end_date,
                created_by_id=g.user.id,
                billing_type=billing_type_enum,
                hourly_rate=hourly_rate if hourly_rate else None,
                billing_notes=billing_notes
            )
            project_repo.save()
            flash(f'Project "{name}" created successfully!', 'success')
            return redirect(url_for('projects.admin_projects'))
        else:
            validator.flash_errors()

    # Get available teams and categories for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).order_by(Team.name).all()
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()
    
    # Get company currency
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    currency_symbol = get_currency_symbol(currency)
    
    return render_template('create_project.html', 
                         title='Create Project', 
                         teams=teams, 
                         categories=categories,
                         currency=currency,
                         currency_symbol=currency_symbol)


@projects_bp.route('/edit/<int:project_id>', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def edit_project(project_id):
    project_repo = ProjectRepository()
    project = project_repo.get_by_id_and_company(project_id, g.user.company_id)
    
    if not project:
        abort(404)

    if request.method == 'POST':
        validator = FormValidator()
        
        name = request.form.get('name')
        description = request.form.get('description')
        code = request.form.get('code')
        team_id = request.form.get('team_id') or None
        category_id = request.form.get('category_id') or None
        is_active = request.form.get('is_active') == 'on'
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Billing fields
        billing_type = request.form.get('billing_type', 'NON_BILLABLE')
        if not billing_type:
            billing_type = 'NON_BILLABLE'
        hourly_rate = request.form.get('hourly_rate')
        billing_notes = request.form.get('billing_notes')

        # Validate required fields
        validator.validate_required(name, 'Project name')
        validator.validate_required(code, 'Project code')
        
        # Validate code uniqueness (exclude current project)
        if validator.is_valid() and code != project.code:
            validator.validate_unique(Project, 'code', code, company_id=g.user.company_id)

        # Parse dates
        start_date = validator.parse_date(start_date_str, 'Start date')
        end_date = validator.parse_date(end_date_str, 'End date')
        
        # Validate date range
        if start_date and end_date:
            validator.validate_date_range(start_date, end_date)
        
        # Validate billing fields
        try:
            # Validate billing type is a valid enum
            billing_type_enum = BillingType[billing_type]
        except KeyError:
            validator.add_error(f'Invalid billing type: {billing_type}')
            billing_type_enum = BillingType.NON_BILLABLE
        
        if billing_type == 'HOURLY' and not hourly_rate:
            validator.add_error('Hourly rate is required for hourly billing')
        
        if hourly_rate:
            try:
                hourly_rate = float(hourly_rate)
                if hourly_rate < 0:
                    validator.add_error('Hourly rate must be positive')
            except ValueError:
                validator.add_error('Invalid hourly rate')

        if validator.is_valid():
            project_repo.update(project,
                name=name,
                description=description,
                code=code.upper(),
                team_id=int(team_id) if team_id else None,
                category_id=int(category_id) if category_id else None,
                is_active=is_active,
                start_date=start_date,
                end_date=end_date,
                billing_type=billing_type_enum,
                hourly_rate=hourly_rate if hourly_rate else None,
                billing_notes=billing_notes
            )
            project_repo.save()
            flash(f'Project "{name}" updated successfully!', 'success')
            return redirect(url_for('projects.admin_projects'))
        else:
            validator.flash_errors()

    # Get available teams and categories for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).order_by(Team.name).all()
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()
    
    # Get company currency
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    currency_symbol = get_currency_symbol(currency)

    return render_template('edit_project.html', 
                         title='Edit Project', 
                         project=project, 
                         teams=teams, 
                         categories=categories,
                         currency=currency,
                         currency_symbol=currency_symbol)


@projects_bp.route('/delete/<int:project_id>', methods=['POST'])
@company_required
def delete_project(project_id):
    # Check if user is admin or system admin
    if g.user.role not in [Role.ADMIN, Role.SYSTEM_ADMIN]:
        flash('You do not have permission to delete projects.', 'error')
        return redirect(url_for('projects.admin_projects'))
    
    project_repo = ProjectRepository()
    project = project_repo.get_by_id_and_company(project_id, g.user.company_id)
    
    if not project:
        abort(404)

    project_name = project.name
    
    try:
        # Import models needed for cascading deletions
        from models import Sprint, SubTask, TaskDependency, Comment
        
        # Delete all related data in the correct order
        
        # Delete time entries first (they reference tasks)
        # Delete by project_id
        TimeEntry.query.filter_by(project_id=project_id).delete()
        
        # Also delete time entries that reference tasks in this project
        TimeEntry.query.filter(TimeEntry.task_id.in_(
            db.session.query(Task.id).filter(Task.project_id == project_id)
        )).delete(synchronize_session=False)
        
        # Delete comments on tasks in this project
        Comment.query.filter(Comment.task_id.in_(
            db.session.query(Task.id).filter(Task.project_id == project_id)
        )).delete(synchronize_session=False)
        
        # Delete subtasks
        SubTask.query.filter(SubTask.task_id.in_(
            db.session.query(Task.id).filter(Task.project_id == project_id)
        )).delete(synchronize_session=False)
        
        # Delete task dependencies
        TaskDependency.query.filter(
            TaskDependency.blocked_task_id.in_(
                db.session.query(Task.id).filter(Task.project_id == project_id)
            ) | TaskDependency.blocking_task_id.in_(
                db.session.query(Task.id).filter(Task.project_id == project_id)
            )
        ).delete(synchronize_session=False)
        
        # Delete tasks (after all references are removed)
        Task.query.filter_by(project_id=project_id).delete()
        
        # Delete sprints
        Sprint.query.filter_by(project_id=project_id).delete()
        
        # Finally, delete the project
        project_repo.delete(project)
        db.session.commit()
        
        flash(f'Project "{project_name}" and all related data have been permanently deleted.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {str(e)}', 'error')
        return redirect(url_for('projects.edit_project', project_id=project_id))

    return redirect(url_for('projects.admin_projects'))


@projects_bp.route('/<int:project_id>/tasks')
@role_required(Role.TEAM_MEMBER)  # All authenticated users can view tasks
@company_required
def manage_project_tasks(project_id):
    project_repo = ProjectRepository()
    project = project_repo.get_by_id_and_company(project_id, g.user.company_id)
    
    if not project:
        abort(404)

    # Check if user has access to this project
    if not project.is_user_allowed(g.user):
        flash('You do not have access to this project.', 'error')
        return redirect(url_for('projects.admin_projects'))

    # Get all tasks for this project
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.created_at.desc()).all()

    # Get team members for assignment dropdown
    if project.team_id:
        # If project is assigned to a specific team, only show team members
        team_members = User.query.filter_by(team_id=project.team_id, company_id=g.user.company_id).all()
    else:
        # If project is available to all teams, show all company users
        team_members = User.query.filter_by(company_id=g.user.company_id).all()

    return render_template('manage_project_tasks.html',
                         title=f'Tasks - {project.name}',
                         project=project,
                         tasks=tasks,
                         team_members=team_members)