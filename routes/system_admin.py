"""
System Administrator routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from models import (db, Company, User, Role, Team, Project, TimeEntry, SystemSettings, 
                   SystemEvent, BrandingSettings, Task, SubTask, TaskDependency, Sprint, 
                   Comment, UserPreferences, UserDashboard, WorkConfig, CompanySettings, 
                   CompanyWorkConfig, ProjectCategory, Note, NoteFolder, NoteShare, 
                   Announcement, CompanyInvitation)
from routes.auth import system_admin_required
from flask import session
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

system_admin_bp = Blueprint('system_admin', __name__, url_prefix='/system-admin')


@system_admin_bp.route('/dashboard')
@system_admin_required
def system_admin_dashboard():
    """System Administrator Dashboard - view all data across companies"""

    # Global statistics
    total_companies = Company.query.count()
    total_users = User.query.count()
    total_teams = Team.query.count()
    total_projects = Project.query.count()
    total_time_entries = TimeEntry.query.count()

    # System admin count
    system_admins = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()
    regular_admins = User.query.filter_by(role=Role.ADMIN).count()

    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)

    recent_users = User.query.filter(User.created_at >= week_ago).count()
    recent_companies = Company.query.filter(Company.created_at >= week_ago).count()
    recent_time_entries = TimeEntry.query.filter(TimeEntry.arrival_time >= week_ago).count()

    # Top companies by user count
    top_companies = db.session.query(
        Company.name,
        Company.id,
        db.func.count(User.id).label('user_count')
    ).join(User).group_by(Company.id).order_by(db.func.count(User.id).desc()).limit(5).all()

    # Recent companies
    recent_companies_list = Company.query.order_by(Company.created_at.desc()).limit(5).all()

    # System health checks
    orphaned_users = User.query.filter_by(company_id=None).count()
    orphaned_time_entries = TimeEntry.query.filter_by(user_id=None).count()
    blocked_users = User.query.filter_by(is_blocked=True).count()

    return render_template('system_admin_dashboard.html',
                         title='System Administrator Dashboard',
                         total_companies=total_companies,
                         total_users=total_users,
                         total_teams=total_teams,
                         total_projects=total_projects,
                         total_time_entries=total_time_entries,
                         system_admins=system_admins,
                         regular_admins=regular_admins,
                         recent_users=recent_users,
                         recent_companies=recent_companies,
                         recent_time_entries=recent_time_entries,
                         top_companies=top_companies,
                         recent_companies_list=recent_companies_list,
                         orphaned_users=orphaned_users,
                         orphaned_time_entries=orphaned_time_entries,
                         blocked_users=blocked_users)


@system_admin_bp.route('/companies')
@system_admin_required
def system_admin_companies():
    """System admin view of all companies"""
    # Get filter parameters
    search_query = request.args.get('search', '')
    
    # Base query
    query = Company.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            db.or_(
                Company.name.ilike(f'%{search_query}%'),
                Company.slug.ilike(f'%{search_query}%')
            )
        )
    
    # Get all companies
    companies = query.order_by(Company.created_at.desc()).all()
    
    # Create a paginated response object
    from flask_sqlalchemy import Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Paginate companies
    companies_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculate statistics for each company
    company_stats = {}
    for company in companies_paginated.items:
        company_stats[company.id] = {
            'user_count': User.query.filter_by(company_id=company.id).count(),
            'admin_count': User.query.filter_by(company_id=company.id, role=Role.ADMIN).count(),
            'team_count': Team.query.filter_by(company_id=company.id).count(),
            'project_count': Project.query.filter_by(company_id=company.id).count(),
            'active_projects': Project.query.filter_by(company_id=company.id, is_active=True).count(),
        }
    
    return render_template('system_admin_companies.html',
                         title='System Admin - Companies',
                         companies=companies_paginated,
                         company_stats=company_stats,
                         search_query=search_query)


@system_admin_bp.route('/companies/<int:company_id>')
@system_admin_required
def system_admin_company_detail(company_id):
    """System admin detailed view of a specific company"""
    company = Company.query.get_or_404(company_id)
    
    # Get recent time entries count
    week_ago = datetime.now() - timedelta(days=7)
    recent_time_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= week_ago
    ).count()
    
    # Get role distribution
    role_counts = {}
    for role in Role:
        count = User.query.filter_by(company_id=company.id, role=role).count()
        if count > 0:
            role_counts[role.value] = count
    
    # Get users list
    users = User.query.filter_by(company_id=company.id).order_by(User.created_at.desc()).all()
    
    # Get teams list
    teams = Team.query.filter_by(company_id=company.id).all()
    
    # Get projects list
    projects = Project.query.filter_by(company_id=company.id).order_by(Project.created_at.desc()).all()
    
    return render_template('system_admin_company_detail.html',
                         title=f'Company Details - {company.name}',
                         company=company,
                         users=users,
                         teams=teams,
                         projects=projects,
                         recent_time_entries=recent_time_entries,
                         role_counts=role_counts)


@system_admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@system_admin_required
def delete_company(company_id):
    """System Admin: Delete a company and all its data"""
    company = Company.query.get_or_404(company_id)
    company_name = company.name
    
    try:
        # Delete all related data in the correct order to avoid foreign key constraints
        
        # Delete comments (must be before tasks)
        Comment.query.filter(Comment.task_id.in_(
            db.session.query(Task.id).join(Project).filter(Project.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete subtasks
        SubTask.query.filter(SubTask.task_id.in_(
            db.session.query(Task.id).join(Project).filter(Project.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete task dependencies
        TaskDependency.query.filter(
            TaskDependency.blocked_task_id.in_(
                db.session.query(Task.id).join(Project).filter(Project.company_id == company_id)
            ) | TaskDependency.blocking_task_id.in_(
                db.session.query(Task.id).join(Project).filter(Project.company_id == company_id)
            )
        ).delete(synchronize_session=False)
        
        # Delete tasks
        Task.query.filter(Task.project_id.in_(
            db.session.query(Project.id).filter(Project.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete sprints
        Sprint.query.filter(Sprint.project_id.in_(
            db.session.query(Project.id).filter(Project.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete time entries
        TimeEntry.query.filter(TimeEntry.user_id.in_(
            db.session.query(User.id).filter(User.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete projects
        Project.query.filter_by(company_id=company_id).delete()
        
        # Delete teams
        Team.query.filter_by(company_id=company_id).delete()
        
        # Delete user preferences, dashboards, and work configs
        UserPreferences.query.filter(UserPreferences.user_id.in_(
            db.session.query(User.id).filter(User.company_id == company_id)
        )).delete(synchronize_session=False)
        
        UserDashboard.query.filter(UserDashboard.user_id.in_(
            db.session.query(User.id).filter(User.company_id == company_id)
        )).delete(synchronize_session=False)
        
        WorkConfig.query.filter(WorkConfig.user_id.in_(
            db.session.query(User.id).filter(User.company_id == company_id)
        )).delete(synchronize_session=False)
        
        # Delete notes and note-related data
        user_ids_subquery = db.session.query(User.id).filter(User.company_id == company_id).subquery()
        
        # Delete note shares
        NoteShare.query.filter(NoteShare.created_by_id.in_(user_ids_subquery)).delete(synchronize_session=False)
        
        # Delete notes
        Note.query.filter(Note.created_by_id.in_(user_ids_subquery)).delete(synchronize_session=False)
        
        # Delete note folders
        NoteFolder.query.filter(NoteFolder.created_by_id.in_(user_ids_subquery)).delete(synchronize_session=False)
        
        # Delete announcements
        Announcement.query.filter(Announcement.created_by_id.in_(user_ids_subquery)).delete(synchronize_session=False)
        
        # Delete invitations
        CompanyInvitation.query.filter(
            (CompanyInvitation.invited_by_id.in_(user_ids_subquery)) | 
            (CompanyInvitation.accepted_by_user_id.in_(user_ids_subquery))
        ).delete(synchronize_session=False)
        
        # Delete system events associated with users from this company
        SystemEvent.query.filter(SystemEvent.user_id.in_(user_ids_subquery)).delete(synchronize_session=False)
        
        # Clear branding settings updated_by references
        BrandingSettings.query.filter(BrandingSettings.updated_by_id.in_(user_ids_subquery)).update(
            {BrandingSettings.updated_by_id: None}, synchronize_session=False)
        
        # Delete users
        User.query.filter_by(company_id=company_id).delete()
        
        # Delete company settings and work config
        CompanySettings.query.filter_by(company_id=company_id).delete()
        CompanyWorkConfig.query.filter_by(company_id=company_id).delete()
        
        # Delete project categories
        ProjectCategory.query.filter_by(company_id=company_id).delete()
        
        # Finally, delete the company
        db.session.delete(company)
        db.session.commit()
        
        flash(f'Company "{company_name}" and all its data have been permanently deleted.', 'success')
        logger.info(f"System admin {g.user.username} deleted company {company_name} (ID: {company_id})")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting company {company_id}: {str(e)}")
        flash(f'Error deleting company: {str(e)}', 'error')
        return redirect(url_for('system_admin.system_admin_company_detail', company_id=company_id))
    
    return redirect(url_for('system_admin.system_admin_companies'))


@system_admin_bp.route('/time-entries')
@system_admin_required
def system_admin_time_entries():
    """System Admin: View time entries across all companies"""
    page = request.args.get('page', 1, type=int)
    company_filter = request.args.get('company', '')
    per_page = 50

    # Build query properly with explicit joins
    query = db.session.query(
        TimeEntry,
        User.username,
        Company.name.label('company_name'),
        Project.name.label('project_name')
    ).join(
        User, TimeEntry.user_id == User.id
    ).join(
        Company, User.company_id == Company.id
    ).outerjoin(
        Project, TimeEntry.project_id == Project.id
    )

    # Apply company filter
    if company_filter:
        query = query.filter(Company.id == company_filter)

    # Order by arrival time (newest first)
    query = query.order_by(TimeEntry.arrival_time.desc())

    # Paginate
    entries = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get companies for filter dropdown
    companies = Company.query.order_by(Company.name).all()
    
    # Get today's date for the template
    today = datetime.now().date()

    return render_template('system_admin_time_entries.html',
                         title='System Admin - Time Entries',
                         entries=entries,
                         companies=companies,
                         current_company=company_filter,
                         today=today)


@system_admin_bp.route('/settings', methods=['GET', 'POST'])
@system_admin_required
def system_admin_settings():
    """System Admin: Global system settings"""
    if request.method == 'POST':
        # Update system settings
        registration_enabled = request.form.get('registration_enabled') == 'on'
        email_verification = request.form.get('email_verification_required') == 'on'
        tracking_script_enabled = request.form.get('tracking_script_enabled') == 'on'
        tracking_script_code = request.form.get('tracking_script_code', '')

        # Update or create settings
        reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
        if reg_setting:
            reg_setting.value = 'true' if registration_enabled else 'false'
        else:
            reg_setting = SystemSettings(
                key='registration_enabled',
                value='true' if registration_enabled else 'false',
                description='Controls whether new user registration is allowed'
            )
            db.session.add(reg_setting)

        email_setting = SystemSettings.query.filter_by(key='email_verification_required').first()
        if email_setting:
            email_setting.value = 'true' if email_verification else 'false'
        else:
            email_setting = SystemSettings(
                key='email_verification_required',
                value='true' if email_verification else 'false',
                description='Controls whether email verification is required for new accounts'
            )
            db.session.add(email_setting)

        tracking_enabled_setting = SystemSettings.query.filter_by(key='tracking_script_enabled').first()
        if tracking_enabled_setting:
            tracking_enabled_setting.value = 'true' if tracking_script_enabled else 'false'
        else:
            tracking_enabled_setting = SystemSettings(
                key='tracking_script_enabled',
                value='true' if tracking_script_enabled else 'false',
                description='Controls whether custom tracking script is enabled'
            )
            db.session.add(tracking_enabled_setting)

        tracking_code_setting = SystemSettings.query.filter_by(key='tracking_script_code').first()
        if tracking_code_setting:
            tracking_code_setting.value = tracking_script_code
        else:
            tracking_code_setting = SystemSettings(
                key='tracking_script_code',
                value=tracking_script_code,
                description='Custom tracking script code (HTML/JavaScript)'
            )
            db.session.add(tracking_code_setting)

        db.session.commit()
        flash('System settings updated successfully.', 'success')
        return redirect(url_for('system_admin.system_admin_settings'))

    # Get current settings
    settings = {}
    all_settings = SystemSettings.query.all()
    for setting in all_settings:
        if setting.key == 'registration_enabled':
            settings['registration_enabled'] = setting.value == 'true'
        elif setting.key == 'email_verification_required':
            settings['email_verification_required'] = setting.value == 'true'
        elif setting.key == 'tracking_script_enabled':
            settings['tracking_script_enabled'] = setting.value == 'true'
        elif setting.key == 'tracking_script_code':
            settings['tracking_script_code'] = setting.value

    # System statistics
    total_companies = Company.query.count()
    total_users = User.query.count()
    total_system_admins = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()

    return render_template('system_admin_settings.html',
                         title='System Administrator Settings',
                         settings=settings,
                         total_companies=total_companies,
                         total_users=total_users,
                         total_system_admins=total_system_admins)


@system_admin_bp.route('/health')
@system_admin_required
def system_admin_health():
    """System Admin: System health check and event log"""
    # Get system health summary
    health_summary = SystemEvent.get_system_health_summary()

    # Get recent events (last 7 days)
    recent_events = SystemEvent.get_recent_events(days=7, limit=100)

    # Get events by severity for quick stats
    errors = SystemEvent.get_events_by_severity('error', days=7, limit=20)
    warnings = SystemEvent.get_events_by_severity('warning', days=7, limit=20)

    # System metrics
    now = datetime.now()

    # Database connection test
    db_healthy = True
    db_error = None
    try:
        db.session.execute('SELECT 1')
    except Exception as e:
        db_healthy = False
        db_error = str(e)
        SystemEvent.log_event(
            'database_check_failed',
            f'Database health check failed: {str(e)}',
            'system',
            'error'
        )

    # Application uptime (approximate based on first event)
    first_event = SystemEvent.query.order_by(SystemEvent.timestamp.asc()).first()
    uptime_start = first_event.timestamp if first_event else now
    uptime_duration = now - uptime_start

    # Recent activity stats
    today = now.date()
    today_events = SystemEvent.query.filter(
        func.date(SystemEvent.timestamp) == today
    ).count()
    
    # Calculate 24-hour error count
    yesterday = now - timedelta(days=1)
    error_count_24h = SystemEvent.query.filter(
        SystemEvent.timestamp >= yesterday,
        SystemEvent.severity == 'error'
    ).count()

    # Log the health check
    SystemEvent.log_event(
        'system_health_check',
        f'System health check performed by {session.get("username", "unknown")}',
        'system',
        'info',
        user_id=session.get('user_id'),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    return render_template('system_admin_health.html',
                         title='System Health Check',
                         health_summary=health_summary,
                         recent_events=recent_events,
                         errors=errors,
                         warnings=warnings,
                         db_healthy=db_healthy,
                         db_error=db_error,
                         uptime_duration=uptime_duration,
                         today_events=today_events,
                         error_count_24h=error_count_24h)


@system_admin_bp.route('/branding', methods=['GET', 'POST'])
@system_admin_required
def branding():
    """System Admin: Branding settings"""
    if request.method == 'POST':
        branding = BrandingSettings.get_current()
        
        # Handle form data
        branding.app_name = request.form.get('app_name', g.branding.app_name).strip()
        branding.logo_alt_text = request.form.get('logo_alt_text', '').strip()
        branding.primary_color = request.form.get('primary_color', '#007bff').strip()
        
        # Handle imprint settings
        branding.imprint_enabled = 'imprint_enabled' in request.form
        branding.imprint_title = request.form.get('imprint_title', 'Imprint').strip()
        branding.imprint_content = request.form.get('imprint_content', '').strip()
        
        branding.updated_by_id = g.user.id
        
        # Handle logo upload
        if 'logo_file' in request.files:
            logo_file = request.files['logo_file']
            if logo_file and logo_file.filename:
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'branding')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the file with a timestamp to avoid conflicts
                import time
                filename = f"logo_{int(time.time())}_{logo_file.filename}"
                logo_path = os.path.join(upload_dir, filename)
                logo_file.save(logo_path)
                branding.logo_filename = filename
        
        # Handle favicon upload
        if 'favicon_file' in request.files:
            favicon_file = request.files['favicon_file']
            if favicon_file and favicon_file.filename:
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'branding')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the file with a timestamp to avoid conflicts
                import time
                filename = f"favicon_{int(time.time())}_{favicon_file.filename}"
                favicon_path = os.path.join(upload_dir, filename)
                favicon_file.save(favicon_path)
                branding.favicon_filename = filename
        
        db.session.commit()
        flash('Branding settings updated successfully.', 'success')
        return redirect(url_for('system_admin.branding'))
    
    # Get current branding settings
    branding = BrandingSettings.get_current()
    
    return render_template('system_admin_branding.html',
                         title='System Administrator - Branding Settings',
                         branding=branding)