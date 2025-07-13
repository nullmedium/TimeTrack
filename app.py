from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, g, Response, send_file, abort
from flask_migrate import Migrate
from models import db, TimeEntry, WorkConfig, User, SystemSettings, Team, Role, Project, Company, CompanyWorkConfig, CompanySettings, UserPreferences, WorkRegion, AccountType, ProjectCategory, Task, SubTask, TaskStatus, TaskPriority, TaskDependency, Sprint, SprintStatus, Announcement, SystemEvent, WidgetType, UserDashboard, DashboardWidget, WidgetTemplate, Comment, CommentVisibility, BrandingSettings, CompanyInvitation, Note, NoteFolder, NoteShare
from data_formatting import (
    format_duration, prepare_export_data, prepare_team_hours_export_data,
    format_table_data, format_graph_data, format_team_data, format_burndown_data
)
# Data export functions moved to routes/export.py and routes/export_api.py
from time_utils import apply_time_rounding, round_duration_to_interval, get_user_rounding_settings
import logging
from datetime import datetime, time, timedelta
import os
import csv
import io
import pandas as pd
from sqlalchemy import func
from functools import wraps
from flask_mail import Mail, Message
from dotenv import load_dotenv
from password_utils import PasswordValidator
from werkzeug.security import check_password_hash

# Import blueprints
from routes.notes import notes_bp
from routes.notes_download import notes_download_bp
from routes.notes_api import notes_api_bp
from routes.notes_public import notes_public_bp
from routes.tasks import tasks_bp, get_filtered_tasks_for_burndown
from routes.tasks_api import tasks_api_bp
from routes.sprints import sprints_bp
from routes.sprints_api import sprints_api_bp
from routes.teams import teams_bp
from routes.teams_api import teams_api_bp
from routes.projects import projects_bp
from routes.projects_api import projects_api_bp
from routes.company import companies_bp, setup_company as company_setup
from routes.company_api import company_api_bp
from routes.users import users_bp
from routes.users_api import users_api_bp
from routes.system_admin import system_admin_bp
from routes.announcements import announcements_bp
from routes.export import export_bp
from routes.export_api import export_api_bp
from routes.organization import organization_bp

# Import auth decorators from routes.auth
from routes.auth import login_required, admin_required, system_admin_required, role_required, company_required

# Import utility functions
from utils.auth import is_system_admin, can_access_system_settings
from security_headers import init_security
from utils.settings import get_system_setting

# Import analytics data function from export module
from routes.export_api import get_filtered_analytics_data

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////data/timetrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_timetrack')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts for 7 days

# Fix for HTTPS behind proxy (nginx, load balancer, etc)
# This ensures forms use https:// URLs when behind a reverse proxy
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Trust X-Forwarded-For
    x_proto=1,    # Trust X-Forwarded-Proto
    x_host=1,     # Trust X-Forwarded-Host
    x_prefix=1    # Trust X-Forwarded-Prefix
)

# Force HTTPS URL scheme in production
if not app.debug and os.environ.get('FORCE_HTTPS', 'false').lower() in ['true', '1', 'yes']:
    app.config['PREFERRED_URL_SCHEME'] = 'https'

# Initialize security headers
init_security(app)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.example.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 587)
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@example.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'TimeTrack <noreply@timetrack.com>')  # Will be overridden by branding in mail sending functions

# Log mail configuration (without password)
logger.info(f"Mail server: {app.config['MAIL_SERVER']}")
logger.info(f"Mail port: {app.config['MAIL_PORT']}")
logger.info(f"Mail use TLS: {app.config['MAIL_USE_TLS']}")
logger.info(f"Mail username: {app.config['MAIL_USERNAME']}")
logger.info(f"Mail default sender: {app.config['MAIL_DEFAULT_SENDER']}")

mail = Mail(app)

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(notes_bp)
app.register_blueprint(notes_download_bp)
app.register_blueprint(notes_api_bp)
app.register_blueprint(notes_public_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(tasks_api_bp)
app.register_blueprint(sprints_bp)
app.register_blueprint(sprints_api_bp)
app.register_blueprint(teams_bp)
app.register_blueprint(teams_api_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(projects_api_bp)
app.register_blueprint(companies_bp)
app.register_blueprint(company_api_bp)
app.register_blueprint(users_bp)
app.register_blueprint(users_api_bp)
app.register_blueprint(system_admin_bp)
app.register_blueprint(announcements_bp)
app.register_blueprint(export_bp)
app.register_blueprint(export_api_bp)
app.register_blueprint(organization_bp)

# Import and register invitations blueprint
from routes.invitations import invitations_bp
app.register_blueprint(invitations_bp)

# Migration functions removed - migrations are now handled by startup.sh

def init_system_settings():
    """Initialize system settings with default values if they don't exist"""
    if not SystemSettings.query.filter_by(key='registration_enabled').first():
        print("Adding registration_enabled system setting...")
        reg_setting = SystemSettings(
            key='registration_enabled',
            value='true',
            description='Controls whether new user registration is allowed'
        )
        db.session.add(reg_setting)

    if not SystemSettings.query.filter_by(key='email_verification_required').first():
        print("Adding email_verification_required system setting...")
        email_setting = SystemSettings(
            key='email_verification_required',
            value='true',
            description='Controls whether email verification is required for new user accounts'
        )
        db.session.add(email_setting)

# Data migration functions removed - migrations are now handled by startup.sh

# Call this function during app initialization
@app.before_first_request
def initialize_app():
    # Initialize system settings only
    with app.app_context():
        init_system_settings()

# Add this after initializing the app but before defining routes
@app.context_processor
def inject_globals():
    """Make certain variables available to all templates."""
    # Get active announcements for current user
    active_announcements = []
    if g.user:
        try:
            active_announcements = Announcement.get_active_announcements_for_user(g.user)
        except Exception as e:
            # If there's a database error, rollback and continue
            db.session.rollback()
            logger.error(f"Error fetching announcements: {e}")
            active_announcements = []

    # Get tracking script settings
    tracking_script_enabled = False
    tracking_script_code = ''

    try:
        tracking_enabled_setting = SystemSettings.query.filter_by(key='tracking_script_enabled').first()
        if tracking_enabled_setting:
            tracking_script_enabled = tracking_enabled_setting.value == 'true'

        tracking_code_setting = SystemSettings.query.filter_by(key='tracking_script_code').first()
        if tracking_code_setting:
            tracking_script_code = tracking_code_setting.value
    except Exception as e:
        # Rollback on any database error
        db.session.rollback()
        logger.error(f"Error fetching system settings: {e}")
    except Exception:
        pass  # In case database isn't available yet
    return {
        'Role': Role,
        'AccountType': AccountType,
        'current_year': datetime.now().year,
        'today': datetime.now().date(),
        'now': datetime.now,
        'active_announcements': active_announcements,
        'tracking_script_enabled': tracking_script_enabled,
        'tracking_script_code': tracking_script_code
    }

# Template filters for date/time formatting
@app.template_filter('from_json')
def from_json_filter(json_str):
    """Parse JSON string to Python object."""
    if not json_str:
        return []
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []

@app.template_filter('format_date')
def format_date_filter(dt):
    """Format date according to user preferences."""
    if not dt or not g.user:
        return dt.strftime('%Y-%m-%d') if dt else ''

    from time_utils import format_date_by_preference, get_user_format_settings
    date_format, _ = get_user_format_settings(g.user)
    return format_date_by_preference(dt, date_format)

@app.template_filter('format_time')
def format_time_filter(dt):
    """Format time according to user preferences."""
    if not dt or not g.user:
        return dt.strftime('%H:%M:%S') if dt else ''

    from time_utils import format_time_by_preference, get_user_format_settings
    _, time_format_24h = get_user_format_settings(g.user)
    return format_time_by_preference(dt, time_format_24h)

@app.template_filter('format_time_short')
def format_time_short_filter(dt):
    """Format time without seconds according to user preferences."""
    if not dt or not g.user:
        return dt.strftime('%H:%M') if dt else ''

    from time_utils import format_time_short_by_preference, get_user_format_settings
    _, time_format_24h = get_user_format_settings(g.user)
    return format_time_short_by_preference(dt, time_format_24h)

@app.template_filter('format_datetime')
def format_datetime_filter(dt):
    """Format datetime according to user preferences."""
    if not dt or not g.user:
        return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''

    from time_utils import format_datetime_by_preference, get_user_format_settings
    date_format, time_format_24h = get_user_format_settings(g.user)
    return format_datetime_by_preference(dt, date_format, time_format_24h)

@app.template_filter('format_duration')
def format_duration_filter(duration_seconds):
    """Format duration in readable format."""
    if duration_seconds is None:
        return '00:00:00'

    from time_utils import format_duration_readable
    return format_duration_readable(duration_seconds)

# Authentication decorator
# Auth decorators have been moved to routes.auth
# Utility functions have been moved to utils modules

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        g.company = None
    else:
        g.user = User.query.get(user_id)
        if g.user:
            # Set company context
            if g.user.company_id:
                g.company = Company.query.get(g.user.company_id)
            else:
                g.company = None

            # Check if user has email but not verified
            if g.user and not g.user.is_verified and g.user.email:
                # Add a flag for templates to show email verification nag
                g.show_email_verification_nag = True
            else:
                g.show_email_verification_nag = False

            # Check if user has no email at all
            if g.user and not g.user.email:
                g.show_email_nag = True
            else:
                g.show_email_nag = False
        else:
            g.company = None

    # Load branding settings
    g.branding = BrandingSettings.get_current()

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Company setup route - delegates to imported function"""
    return company_setup()

@app.route('/robots.txt')
def robots_txt():
    """Generate robots.txt for search engines"""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /export/",
        "Disallow: /profile/",
        "Disallow: /config/",
        "Disallow: /teams/",
        "Disallow: /projects/",
        "Disallow: /logout",
        f"Sitemap: {request.host_url}sitemap.xml",
        "",
        "# TimeTrack - Open Source Time Tracking Software",
        "# https://github.com/nullmedium/TimeTrack"
    ]
    return Response('\n'.join(lines), mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Generate XML sitemap for search engines"""
    pages = []
    
    # Static pages accessible without login
    static_pages = [
        {'loc': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': '/login', 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': '/register', 'priority': '0.9', 'changefreq': 'monthly'},
        {'loc': '/forgot_password', 'priority': '0.5', 'changefreq': 'monthly'},
    ]
    
    for page in static_pages:
        pages.append({
            'loc': request.host_url[:-1] + page['loc'],
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'priority': page['priority'],
            'changefreq': page['changefreq']
        })
    
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        sitemap_xml += '  <url>\n'
        sitemap_xml += f'    <loc>{page["loc"]}</loc>\n'
        sitemap_xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
        sitemap_xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        sitemap_xml += f'    <priority>{page["priority"]}</priority>\n'
        sitemap_xml += '  </url>\n'
    
    sitemap_xml += '</urlset>'
    
    return Response(sitemap_xml, mimetype='application/xml')

@app.route('/')
def home():
    if g.user:
        # Get active time entry
        active_entry = TimeEntry.query.filter_by(
            user_id=g.user.id,
            departure_time=None
        ).first()

        # Get recent time entries (limit to 50 like the time_tracking route)
        history = TimeEntry.query.filter_by(user_id=g.user.id).order_by(
            TimeEntry.arrival_time.desc()
        ).limit(50).all()

        # Get available projects
        available_projects = []
        if g.user.company_id:
            if g.user.role == Role.ADMIN:
                # Admin can see all company projects
                available_projects = Project.query.filter_by(
                    company_id=g.user.company_id,
                    is_active=True
                ).order_by(Project.code).all()
            else:
                # Regular users see only their assigned projects
                all_projects = Project.query.filter_by(
                    company_id=g.user.company_id,
                    is_active=True
                ).all()
                for project in all_projects:
                    if project.is_user_allowed(g.user):
                        available_projects.append(project)

        # Calculate statistics (if we want the stats section to show)
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Today's hours
        today_entries = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            func.date(TimeEntry.arrival_time) == today
        ).all()
        today_hours = sum(entry.duration or 0 for entry in today_entries)

        # This week's hours
        week_entries = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            func.date(TimeEntry.arrival_time) >= week_start
        ).all()
        week_hours = sum(entry.duration or 0 for entry in week_entries)

        # This month's hours
        month_entries = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            func.date(TimeEntry.arrival_time) >= month_start
        ).all()
        month_hours = sum(entry.duration or 0 for entry in month_entries)

        # Active projects (projects with recent entries)
        active_project_ids = db.session.query(TimeEntry.project_id).filter(
            TimeEntry.user_id == g.user.id,
            TimeEntry.project_id.isnot(None),
            TimeEntry.arrival_time >= datetime.now() - timedelta(days=30)
        ).distinct().all()
        active_projects = [p for p in available_projects if p.id in [pid[0] for pid in active_project_ids]]

        return render_template('index.html', title='Home',
                             active_entry=active_entry,
                             history=history,
                             available_projects=available_projects,
                             today_hours=today_hours,
                             week_hours=week_hours,
                             month_hours=month_hours,
                             active_projects=active_projects)
    else:
        return render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user:
            # Fix role if it's a string or None
            if isinstance(user.role, str) or user.role is None:
                # Map string role values to enum values
                role_mapping = {
                    'Team Member': Role.TEAM_MEMBER,
                    'TEAM_MEMBER': Role.TEAM_MEMBER,
                    'Team Leader': Role.TEAM_LEADER,
                    'TEAM_LEADER': Role.TEAM_LEADER,
                    'Supervisor': Role.SUPERVISOR,
                    'SUPERVISOR': Role.SUPERVISOR,
                    'Administrator': Role.ADMIN,
                    'ADMIN': Role.ADMIN
                }

                if isinstance(user.role, str):
                    user.role = role_mapping.get(user.role, Role.TEAM_MEMBER)
                else:
                    user.role = Role.ADMIN if user.role == Role.ADMIN else Role.TEAM_MEMBER

                db.session.commit()

            # Now proceed with password check
            if user.check_password(password):
                # Check if user is blocked
                if user.is_blocked:
                    flash('Your account has been disabled. Please contact an administrator.', 'error')
                    return render_template('login.html')

                # Check if 2FA is enabled
                if user.two_factor_enabled:
                    # Store user ID for 2FA verification
                    session['2fa_user_id'] = user.id
                    return redirect(url_for('verify_2fa'))
                else:
                    # Continue with normal login process
                    session['user_id'] = user.id
                    session['username'] = user.username
                    session['role'] = user.role.value

                    # Log successful login
                    SystemEvent.log_event(
                        'user_login',
                        f'User {user.username} logged in successfully',
                        'auth',
                        'info',
                        user_id=user.id,
                        company_id=user.company_id,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )

                    flash('Login successful!', 'success')
                    return redirect(url_for('home'))

        # Log failed login attempt
        SystemEvent.log_event(
            'login_failed',
            f'Failed login attempt for username: {username}',
            'auth',
            'warning',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        flash('Invalid username or password', 'error')

    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    # Log logout event before clearing session
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            SystemEvent.log_event(
                'user_logout',
                f'User {user.username} logged out',
                'auth',
                'info',
                user_id=user.id,
                company_id=user.company_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if registration is enabled
    registration_enabled = get_system_setting('registration_enabled', 'true') == 'true'

    if not registration_enabled:
        flash('Registration is currently disabled by the administrator.', 'error')
        return redirect(url_for('login'))

    # No longer redirect to company setup - users can now create companies during registration

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        company_code = request.form.get('company_code', '').strip()
        registration_type = request.form.get('registration_type', 'company')

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'

        # Validate password strength
        if not error:
            validator = PasswordValidator()
            is_valid, password_errors = validator.validate(password)
            if not is_valid:
                error = password_errors[0]  # Show first error

        # Find company by code or create new one if no code provided
        company = None
        if company_code:
            # User provided a code - try to join existing company
            company = Company.query.filter_by(slug=company_code.lower()).first()
            if not company:
                error = 'Invalid company code'
        else:
            # No code provided - create a new company (only for company registration type)
            if registration_type == 'company' and not error:
                # Generate company name from username
                company_name = f"{username}'s Company"
                company_slug = f"{username.lower()}-company"

                # Ensure unique slug
                base_slug = company_slug
                counter = 1
                while Company.query.filter_by(slug=company_slug).first():
                    company_slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create new company
                company = Company(
                    name=company_name,
                    slug=company_slug,
                    max_users=None,  # Unlimited users
                    is_personal=False  # This is a regular company, not a freelancer workspace
                )
                db.session.add(company)
                db.session.flush()  # Get the company ID without committing

                # Create default work configuration for the company
                preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
                work_config = CompanyWorkConfig(
                    company_id=company.id,
                    standard_hours_per_day=preset['standard_hours_per_day'],
                    standard_hours_per_week=preset['standard_hours_per_week'],
                    work_region=WorkRegion.GERMANY,
                    overtime_enabled=preset['overtime_enabled'],
                    overtime_rate=preset['overtime_rate'],
                    double_time_enabled=preset['double_time_enabled'],
                    double_time_threshold=preset['double_time_threshold'],
                    double_time_rate=preset['double_time_rate'],
                    require_breaks=preset['require_breaks'],
                    break_duration_minutes=preset['break_duration_minutes'],
                    break_after_hours=preset['break_after_hours'],
                    weekly_overtime_threshold=preset['weekly_overtime_threshold'],
                    weekly_overtime_rate=preset['weekly_overtime_rate']
                )
                db.session.add(work_config)

        # Check for existing users within the company
        if company and not error:
            if User.query.filter_by(username=username, company_id=company.id).first():
                error = 'Username already exists in this company'
            elif email and User.query.filter_by(email=email, company_id=company.id).first():
                error = 'Email already registered in this company'

        if error is None and company:
            try:
                # Check if this is the first user account in this company
                is_first_user_in_company = User.query.filter_by(company_id=company.id).count() == 0

                # Check if email verification is required
                email_verification_required = get_system_setting('email_verification_required', 'true') == 'true'

                new_user = User(
                    username=username,
                    email=email,
                    company_id=company.id,
                    is_verified=False
                )
                new_user.set_password(password)

                # Make first user in company an admin with full privileges
                if is_first_user_in_company:
                    new_user.role = Role.ADMIN
                    new_user.is_verified = True  # Auto-verify first user in company
                elif not email_verification_required:
                    # If email verification is disabled, auto-verify new users
                    new_user.is_verified = True

                # Generate verification token (even if not needed, for consistency)

                token = new_user.generate_verification_token()

                db.session.add(new_user)
                db.session.commit()

                if is_first_user_in_company:
                    # First user in company gets admin privileges and is auto-verified
                    logger.info(f"First user account created in company {company.name}: {username} with admin privileges")
                    flash(f'Welcome! You are the first user in {company.name} and have been granted administrator privileges. You can now log in.', 'success')
                elif not email_verification_required:
                    # Email verification is disabled, user can log in immediately
                    logger.info(f"User account created with auto-verification in company {company.name}: {username}")
                    flash('Registration successful! You can now log in.', 'success')
                else:
                    # Send verification email for regular users when verification is required
                    verification_url = url_for('verify_email', token=token, _external=True)
                    msg = Message(f'Verify your {g.branding.app_name} account', recipients=[email])
                    msg.body = f'''Hello {username},

Thank you for registering with {g.branding.app_name}. To complete your registration, please click on the link below:

{verification_url}

This link will expire in 24 hours.

If you did not register for {g.branding.app_name}, please ignore this email.

Best regards,
The {g.branding.app_name} Team
'''
                    mail.send(msg)
                    logger.info(f"Verification email sent to {email}")
                    flash('Registration initiated! Please check your email to verify your account.', 'success')

                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during registration: {str(e)}")
                error = f"An error occurred during registration: {str(e)}"

        flash(error, 'error')

    return render_template('register.html', title='Register')

@app.route('/register/freelancer', methods=['GET', 'POST'])
def register_freelancer():
    """Freelancer registration route - creates user without company token"""
    # Check if registration is enabled
    registration_enabled = get_system_setting('registration_enabled', 'true') == 'true'

    if not registration_enabled:
        flash('Registration is currently disabled by the administrator.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        business_name = request.form.get('business_name', '').strip()

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'

        # Validate password strength
        if not error:
            validator = PasswordValidator()
            is_valid, password_errors = validator.validate(password)
            if not is_valid:
                error = password_errors[0]  # Show first error

        # Check for existing users globally (freelancers get unique usernames/emails)
        if not error:
            if User.query.filter_by(username=username).first():
                error = 'Username already exists'
            elif email and User.query.filter_by(email=email).first():
                error = 'Email already registered'

        if error is None:
            try:
                # Create personal company for freelancer
                company_name = business_name if business_name else f"{username}'s Workspace"

                # Generate unique company slug
                import re
                slug = re.sub(r'[^\w\s-]', '', company_name.lower())
                slug = re.sub(r'[-\s]+', '-', slug).strip('-')

                # Ensure slug uniqueness
                base_slug = slug
                counter = 1
                while Company.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create personal company
                personal_company = Company(
                    name=company_name,
                    slug=slug,
                    description=f"Personal workspace for {username}",
                    is_personal=True,
                    max_users=1  # Limit to single user
                )

                db.session.add(personal_company)
                db.session.flush()  # Get company ID

                # Create freelancer user
                new_user = User(
                    username=username,
                    email=email,
                    company_id=personal_company.id,
                    account_type=AccountType.FREELANCER,
                    business_name=business_name if business_name else None,
                    role=Role.ADMIN,  # Freelancers are admins of their personal company
                    is_verified=True  # Auto-verify freelancers
                )
                new_user.set_password(password)

                db.session.add(new_user)
                db.session.commit()

                logger.info(f"Freelancer account created: {username} with personal company: {company_name}")
                flash(f'Welcome {username}! Your freelancer account has been created successfully. You can now log in.', 'success')

                return redirect(url_for('login'))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during freelancer registration: {str(e)}")
                error = f"An error occurred during registration: {str(e)}"

        if error:
            flash(error, 'error')

    return render_template('register_freelancer.html', title='Register as Freelancer')

@app.route('/register/invitation/<token>', methods=['GET', 'POST'])
def register_with_invitation(token):
    """Registration route for users with an invitation"""
    # Find the invitation
    invitation = CompanyInvitation.query.filter_by(token=token).first()

    if not invitation:
        flash('Invalid invitation link', 'error')
        return redirect(url_for('register'))

    if not invitation.is_valid():
        if invitation.accepted:
            flash('This invitation has already been used', 'error')
        else:
            flash('This invitation has expired', 'error')
        return redirect(url_for('register'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'

        # Validate password strength
        if not error:
            validator = PasswordValidator()
            is_valid, password_errors = validator.validate(password)
            if not is_valid:
                error = password_errors[0]

        # Check if username already exists in the company
        if not error:
            if User.query.filter_by(username=username, company_id=invitation.company_id).first():
                error = 'Username already exists in this company'

        if error is None:
            try:
                # Create the user
                new_user = User(
                    username=username,
                    email=invitation.email,
                    company_id=invitation.company_id,
                    role=Role[invitation.role.upper().replace(' ', '_')],
                    is_verified=True  # Pre-verified through invitation
                )
                new_user.set_password(password)

                db.session.add(new_user)

                # Mark invitation as accepted
                invitation.accepted = True
                invitation.accepted_at = datetime.now()
                invitation.accepted_by_user_id = new_user.id

                db.session.commit()

                logger.info(f"User {username} created through invitation for company {invitation.company.name}")
                flash(f'Welcome to {invitation.company.name}! Your account has been created. Please log in.', 'success')

                return redirect(url_for('login'))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during invitation registration: {str(e)}")
                error = 'An error occurred during registration. Please try again.'

        if error:
            flash(error, 'error')

    # GET request - show the registration form
    return render_template('register_invitation.html',
                         invitation=invitation,
                         title='Accept Invitation')

# Setup company route is now imported from company module
app.add_url_rule('/setup_company', 'setup_company', company_setup, methods=['GET', 'POST'])
@app.route('/verify_email/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()

    if not user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('login'))

    if user.verify_token(token):
        db.session.commit()
        flash('Email verified successfully! You can now log in.', 'success')
    else:
        flash('Invalid or expired verification link.', 'error')

    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        
        if not username_or_email:
            flash('Please enter your username or email address.', 'error')
            return render_template('forgot_password.html', title='Forgot Password')
        
        # Try to find user by username or email
        user = User.query.filter(
            db.or_(
                User.username == username_or_email,
                User.email == username_or_email
            )
        ).first()
        
        if user and user.email:
            # Generate reset token
            token = user.generate_password_reset_token()
            
            # Send reset email
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message(
                f'Password Reset Request - {g.branding.app_name if g.branding else "TimeTrack"}',
                recipients=[user.email]
            )
            msg.body = f'''Hello {user.username},

You have requested to reset your password for {g.branding.app_name if g.branding else "TimeTrack"}.

To reset your password, please click on the link below:
{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.

Best regards,
The {g.branding.app_name if g.branding else "TimeTrack"} Team
'''
            
            try:
                mail.send(msg)
                logger.info(f"Password reset email sent to user {user.username}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {str(e)}")
                flash('Failed to send reset email. Please contact support.', 'error')
                return render_template('forgot_password.html', title='Forgot Password')
        
        # Always show success message to prevent user enumeration
        flash('If an account exists with that username or email address, we have sent a password reset link.', 'success')
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', title='Forgot Password')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    # Find user by reset token
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user or not user.verify_password_reset_token(token):
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        error = None
        if not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'
        
        # Validate password strength
        if not error:
            validator = PasswordValidator()
            is_valid, password_errors = validator.validate(password)
            if not is_valid:
                error = password_errors[0]
        
        if error:
            flash(error, 'error')
            return render_template('reset_password.html', token=token, title='Reset Password')
        
        # Update password
        user.set_password(password)
        user.clear_password_reset_token()
        db.session.commit()
        
        logger.info(f"Password reset successful for user {user.username}")
        flash('Your password has been reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token, title='Reset Password')

@app.route('/dashboard')
@role_required(Role.TEAM_MEMBER)
@company_required
def dashboard():
    """User dashboard with configurable widgets - DISABLED due to widget issues."""
    # Redirect to home page instead of dashboard
    flash('Dashboard is temporarily disabled. Redirecting to home page.', 'info')
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate input
        error = None
        if not email:
            error = 'Email is required'
        elif email != user.email and User.query.filter_by(email=email).first():
            error = 'Email already registered'

        # Password change validation
        if new_password:
            if not current_password:
                error = 'Current password is required to set a new password'
            elif not user.check_password(current_password):
                error = 'Current password is incorrect'
            elif new_password != confirm_password:
                error = 'New passwords do not match'
            else:
                # Validate password strength
                validator = PasswordValidator()
                is_valid, password_errors = validator.validate(new_password)
                if not is_valid:
                    error = password_errors[0]  # Show first error

        if error is None:
            user.email = email

            if new_password:
                user.set_password(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

        flash(error, 'error')

    return render_template('profile.html', title='My Profile', user=user)

@app.route('/update-avatar', methods=['POST'])
@login_required
def update_avatar():
    """Update user avatar URL"""
    user = User.query.get(session['user_id'])
    avatar_url = request.form.get('avatar_url', '').strip()

    # Validate URL if provided
    if avatar_url:
        # Basic URL validation
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(avatar_url):
            flash('Please provide a valid URL for your avatar.', 'error')
            return redirect(url_for('profile'))

        # Additional validation for image URLs
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        if not any(avatar_url.lower().endswith(ext) for ext in allowed_extensions):
            # Check if it's a service that doesn't use extensions (like gravatar)
            allowed_services = ['gravatar.com', 'dicebear.com', 'ui-avatars.com', 'avatars.githubusercontent.com']
            if not any(service in avatar_url.lower() for service in allowed_services):
                flash('Avatar URL should point to an image file (JPG, PNG, GIF, WebP, or SVG).', 'error')
                return redirect(url_for('profile'))

    # Update avatar URL (empty string removes custom avatar)
    user.avatar_url = avatar_url if avatar_url else None
    db.session.commit()

    if avatar_url:
        flash('Avatar updated successfully!', 'success')
    else:
        flash('Avatar reset to default.', 'success')

    # Log the avatar change
    SystemEvent.log_event(
        event_type='profile_avatar_updated',
        event_category='user',
        description=f'User {user.username} updated their avatar',
        user_id=user.id,
        company_id=user.company_id
    )

    return redirect(url_for('profile'))

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Handle avatar file upload"""
    import os
    from werkzeug.utils import secure_filename
    import uuid

    user = User.query.get(session['user_id'])

    # Check if file was uploaded
    if 'avatar_file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('profile'))

    file = request.files['avatar_file']

    # Check if file is empty
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('profile'))

    # Validate file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

    if file_ext not in allowed_extensions:
        flash('Invalid file type. Please upload a PNG, JPG, GIF, or WebP image.', 'error')
        return redirect(url_for('profile'))

    # Validate file size (5MB max)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer

    if file_size > 5 * 1024 * 1024:  # 5MB
        flash('File size must be less than 5MB.', 'error')
        return redirect(url_for('profile'))

    # Generate unique filename
    unique_filename = f"{user.id}_{uuid.uuid4().hex}.{file_ext}"

    # Create user avatar directory if it doesn't exist
    avatar_dir = os.path.join(app.static_folder, 'uploads', 'avatars')
    os.makedirs(avatar_dir, exist_ok=True)

    # Save the file
    file_path = os.path.join(avatar_dir, unique_filename)
    file.save(file_path)

    # Delete old avatar file if it exists and is a local upload
    if user.avatar_url and user.avatar_url.startswith('/static/uploads/avatars/'):
        old_file_path = os.path.join(app.root_path, user.avatar_url.lstrip('/'))
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete old avatar: {e}")

    # Update user's avatar URL
    user.avatar_url = f"/static/uploads/avatars/{unique_filename}"
    db.session.commit()

    flash('Avatar uploaded successfully!', 'success')

    # Log the avatar upload
    SystemEvent.log_event(
        event_type='profile_avatar_uploaded',
        event_category='user',
        description=f'User {user.username} uploaded a new avatar',
        user_id=user.id,
        company_id=user.company_id
    )

    return redirect(url_for('profile'))

@app.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        # Verify the TOTP code before enabling 2FA
        totp_code = request.form.get('totp_code')

        if not totp_code:
            flash('Please enter the verification code from your authenticator app.', 'error')
            return redirect(url_for('setup_2fa'))

        try:
            if g.user.verify_2fa_token(totp_code, allow_setup=True):
                g.user.two_factor_enabled = True
                db.session.commit()
                flash('Two-factor authentication has been successfully enabled!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid verification code. Please make sure your device time is synchronized and try again.', 'error')
                return redirect(url_for('setup_2fa'))
        except Exception as e:
            logger.error(f"2FA setup error: {str(e)}")
            flash('An error occurred during 2FA setup. Please try again.', 'error')
            return redirect(url_for('setup_2fa'))

    # GET request - show setup page
    if g.user.two_factor_enabled:
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('profile'))

    # Generate secret if not exists
    if not g.user.two_factor_secret:
        g.user.generate_2fa_secret()
        db.session.commit()

    # Generate QR code
    import qrcode
    import io
    import base64

    qr_uri = g.user.get_2fa_uri(issuer_name=g.branding.app_name)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_uri)
    qr.make(fit=True)

    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    qr_code_b64 = base64.b64encode(img_buffer.getvalue()).decode()

    return render_template('setup_2fa.html',
                         title='Setup Two-Factor Authentication',
                         secret=g.user.two_factor_secret,
                         qr_code=qr_code_b64)

@app.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    password = request.form.get('password')

    if not password or not g.user.check_password(password):
        flash('Please enter your correct password to disable 2FA.', 'error')
        return redirect(url_for('profile'))

    g.user.two_factor_enabled = False
    g.user.two_factor_secret = None
    db.session.commit()

    flash('Two-factor authentication has been disabled.', 'success')
    return redirect(url_for('profile'))

@app.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    # Check if user is in 2FA verification state
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user or not user.two_factor_enabled:
        session.pop('2fa_user_id', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        totp_code = request.form.get('totp_code')

        if user.verify_2fa_token(totp_code):
            # Complete login process
            session.pop('2fa_user_id', None)
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role.value

            # Log successful 2FA login
            SystemEvent.log_event(
                'user_login_2fa',
                f'User {user.username} logged in successfully with 2FA',
                'auth',
                'info',
                user_id=user.id,
                company_id=user.company_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            # Log failed 2FA attempt
            SystemEvent.log_event(
                '2fa_failed',
                f'Failed 2FA verification for user {user.username}',
                'auth',
                'warning',
                user_id=user.id,
                company_id=user.company_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            flash('Invalid verification code. Please try again.', 'error')

    return render_template('verify_2fa.html', title='Two-Factor Authentication')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/imprint')
def imprint():
    """Display the imprint/legal page if enabled"""
    branding = BrandingSettings.get_current()

    # Check if imprint is enabled
    if not branding or not branding.imprint_enabled:
        abort(404)

    title = branding.imprint_title or 'Imprint'
    content = branding.imprint_content or ''

    return render_template('imprint.html',
                         title=title,
                         content=content)

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    # redacted
    return render_template('contact.html', title='Contact')

# We can keep this route as a redirect to home for backward compatibility
@app.route('/timetrack')
@login_required
def timetrack():
    return redirect(url_for('home'))

@app.route('/api/arrive', methods=['POST'])
@login_required
def arrive():
    # Get project, task and notes from request
    project_id = request.json.get('project_id') if request.json else None
    task_id = request.json.get('task_id') if request.json else None
    notes = request.json.get('notes') if request.json else None

    # Validate project access if project is specified
    if project_id:
        project = Project.query.get(project_id)
        if not project or not project.is_user_allowed(g.user):
            return jsonify({'error': 'Invalid or unauthorized project'}), 403

    # Validate task if specified
    if task_id:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Invalid task'}), 400
        # Ensure task belongs to the specified project
        if project_id and task.project_id != int(project_id):
            return jsonify({'error': 'Task does not belong to the specified project'}), 400

    # Create a new time entry with arrival time for the current user
    new_entry = TimeEntry(
        user_id=g.user.id,
        arrival_time=datetime.now(),
        project_id=int(project_id) if project_id else None,
        task_id=int(task_id) if task_id else None,
        notes=notes
    )
    db.session.add(new_entry)
    db.session.commit()

    # Format response with user preferences
    from time_utils import format_datetime_by_preference, get_user_format_settings
    date_format, time_format_24h = get_user_format_settings(g.user)

    return jsonify({
        'id': new_entry.id,
        'arrival_time': format_datetime_by_preference(new_entry.arrival_time, date_format, time_format_24h),
        'project': {
            'id': new_entry.project.id,
            'code': new_entry.project.code,
            'name': new_entry.project.name
        } if new_entry.project else None,
        'notes': new_entry.notes
    })

@app.route('/api/leave/<int:entry_id>', methods=['POST'])
@login_required
def leave(entry_id):
    # Find the time entry for the current user
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()

    # Set the departure time
    departure_time = datetime.now()

    # Apply time rounding if enabled
    rounded_arrival, rounded_departure = apply_time_rounding(entry.arrival_time, departure_time, g.user)
    entry.arrival_time = rounded_arrival
    entry.departure_time = rounded_departure

    # If currently paused, add the final break duration
    if entry.is_paused and entry.pause_start_time:
        final_break_duration = int((rounded_departure - entry.pause_start_time).total_seconds())
        entry.total_break_duration += final_break_duration
        entry.is_paused = False
        entry.pause_start_time = None

    # Apply rounding to break duration if enabled
    interval_minutes, round_to_nearest = get_user_rounding_settings(g.user)
    if interval_minutes > 0:
        entry.total_break_duration = round_duration_to_interval(
            entry.total_break_duration, interval_minutes, round_to_nearest
        )

    # Calculate work duration considering breaks
    entry.duration, effective_break = calculate_work_duration(
        rounded_arrival,
        rounded_departure,
        entry.total_break_duration,
        g.user
    )

    db.session.commit()

    return jsonify({
        'id': entry.id,
        'arrival_time': entry.arrival_time.isoformat(),
        'departure_time': entry.departure_time.isoformat(),
        'duration': entry.duration,
        'total_break_duration': entry.total_break_duration,
        'effective_break_duration': effective_break
    })

# Add this new route to handle pausing/resuming
@app.route('/api/toggle-pause/<int:entry_id>', methods=['POST'])
@login_required
def toggle_pause(entry_id):
    # Find the time entry for the current user
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()

    now = datetime.now()

    if entry.is_paused:
        # Resuming work - calculate break duration
        break_duration = int((now - entry.pause_start_time).total_seconds())
        entry.total_break_duration += break_duration
        entry.is_paused = False
        entry.pause_start_time = None

        message = "Work resumed"
    else:
        # Pausing work
        entry.is_paused = True
        entry.pause_start_time = now

        message = "Work paused"

    db.session.commit()

    return jsonify({
        'id': entry.id,
        'is_paused': entry.is_paused,
        'total_break_duration': entry.total_break_duration,
        'message': message
    })

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    # Get user preferences or create default if none exists
    preferences = UserPreferences.query.filter_by(user_id=g.user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=g.user.id)
        db.session.add(preferences)
        db.session.commit()

    if request.method == 'POST':
        try:
            # Update only user preferences (no company policies)
            preferences.time_format_24h = 'time_format_24h' in request.form
            preferences.date_format = request.form.get('date_format', 'ISO')
            preferences.time_rounding_minutes = int(request.form.get('time_rounding_minutes', 0))
            preferences.round_to_nearest = 'round_to_nearest' in request.form

            db.session.commit()
            flash('Preferences updated successfully!', 'success')
            return redirect(url_for('config'))
        except ValueError:
            flash('Please enter valid values for all fields', 'error')

    # Get company work policies for display (read-only)
    company_config = CompanyWorkConfig.query.filter_by(company_id=g.user.company_id).first()

    # Import time utils for display options
    from time_utils import get_available_rounding_options, get_available_date_formats
    rounding_options = get_available_rounding_options()
    date_format_options = get_available_date_formats()

    return render_template('config.html', title='User Preferences',
                         preferences=preferences,
                         company_config=company_config,
                         rounding_options=rounding_options,
                         date_format_options=date_format_options)

@app.route('/api/delete/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry(entry_id):
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Entry deleted successfully'})

@app.route('/api/time-entry/<int:entry_id>', methods=['GET'])
@login_required
def get_time_entry(entry_id):
    """Get details of a specific time entry"""
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=g.user.id).first_or_404()

    return jsonify({
        'success': True,
        'entry': {
            'id': entry.id,
            'arrival_time': entry.arrival_time.isoformat(),
            'departure_time': entry.departure_time.isoformat() if entry.departure_time else None,
            'project_id': entry.project_id,
            'task_id': entry.task_id,
            'notes': entry.notes,
            'total_break_duration': entry.total_break_duration
        }
    })

@app.route('/time-tracking')
@login_required
@company_required
def time_tracking():
    """Modern time tracking interface"""
    # Get active time entry
    active_entry = TimeEntry.query.filter_by(
        user_id=g.user.id,
        departure_time=None
    ).first()

    # Get recent time entries
    history = TimeEntry.query.filter_by(user_id=g.user.id).order_by(
        TimeEntry.arrival_time.desc()
    ).limit(50).all()

    # Get available projects
    available_projects = []
    if g.user.role == Role.ADMIN:
        # Admin can see all company projects
        available_projects = Project.query.filter_by(
            company_id=g.user.company_id,
            is_active=True
        ).order_by(Project.code).all()
    else:
        # Regular users see only their assigned projects
        all_projects = Project.query.filter_by(
            company_id=g.user.company_id,
            is_active=True
        ).all()
        for project in all_projects:
            if project.is_user_allowed(g.user):
                available_projects.append(project)

    # Calculate statistics
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Today's hours
    today_entries = TimeEntry.query.filter(
        TimeEntry.user_id == g.user.id,
        func.date(TimeEntry.arrival_time) == today
    ).all()
    today_hours = sum(entry.duration or 0 for entry in today_entries)

    # This week's hours
    week_entries = TimeEntry.query.filter(
        TimeEntry.user_id == g.user.id,
        func.date(TimeEntry.arrival_time) >= week_start
    ).all()
    week_hours = sum(entry.duration or 0 for entry in week_entries)

    # This month's hours
    month_entries = TimeEntry.query.filter(
        TimeEntry.user_id == g.user.id,
        func.date(TimeEntry.arrival_time) >= month_start
    ).all()
    month_hours = sum(entry.duration or 0 for entry in month_entries)

    # Active projects (projects with recent entries)
    active_project_ids = db.session.query(TimeEntry.project_id).filter(
        TimeEntry.user_id == g.user.id,
        TimeEntry.project_id.isnot(None),
        TimeEntry.arrival_time >= datetime.now() - timedelta(days=30)
    ).distinct().all()
    active_projects = [p for p in available_projects if p.id in [pid[0] for pid in active_project_ids]]

    return render_template('time_tracking.html',
                         title='Time Tracking',
                         active_entry=active_entry,
                         history=history,
                         available_projects=available_projects,
                         today_hours=today_hours,
                         week_hours=week_hours,
                         month_hours=month_hours,
                         active_projects=active_projects)

@app.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks(project_id):
    """Get tasks for a specific project"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found', 'success': False}), 404

        # Check if user has access to this project
        if not project.is_user_allowed(g.user):
            return jsonify({'error': 'Unauthorized access to project', 'success': False}), 403

        # Get active tasks for the project
        tasks = Task.query.filter(
            Task.project_id == project_id,
            Task.status != TaskStatus.ARCHIVED
        ).order_by(Task.created_at.desc()).all()

        return jsonify({
            'success': True,
            'tasks': [{
                'id': task.id,
                'title': task.name,  # Task model uses 'name' not 'title'
                'status': task.status.value,
                'priority': task.priority.value if task.priority else 'medium'
            } for task in tasks]
        })
    except Exception as e:
        logger.error(f"Error fetching tasks for project {project_id}: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}', 'success': False}), 500

@app.route('/api/update/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()
    data = request.json

    if not data:
        return jsonify({'success': False, 'message': 'No JSON data provided'}), 400

    if 'arrival_time' in data:
        try:
            # Accept only ISO 8601 format
            arrival_time_str = data['arrival_time']
            entry.arrival_time = datetime.fromisoformat(arrival_time_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            return jsonify({'success': False, 'message': f'Invalid arrival time format. Expected ISO 8601: {arrival_time_str}'}), 400

    if 'departure_time' in data and data['departure_time']:
        try:
            # Accept only ISO 8601 format
            departure_time_str = data['departure_time']
            entry.departure_time = datetime.fromisoformat(departure_time_str.replace('Z', '+00:00'))

            # Recalculate duration if both times are present
            if entry.arrival_time and entry.departure_time:
                # Calculate work duration considering breaks
                entry.duration, _ = calculate_work_duration(
                    entry.arrival_time,
                    entry.departure_time,
                    entry.total_break_duration,
                    g.user
                )
        except (ValueError, AttributeError) as e:
            return jsonify({'success': False, 'message': f'Invalid departure time format. Expected ISO 8601: {departure_time_str}'}), 400

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Entry updated successfully',
        'entry': {
            'id': entry.id,
            'arrival_time': entry.arrival_time.isoformat(),
            'departure_time': entry.departure_time.isoformat() if entry.departure_time else None,
            'duration': entry.duration,
            'is_paused': entry.is_paused,
            'total_break_duration': entry.total_break_duration
        }
    })

def calculate_work_duration(arrival_time, departure_time, total_break_duration, user):
    """
    Calculate work duration considering both configured and actual break times.

    Args:
        arrival_time: Datetime of arrival
        departure_time: Datetime of departure
        total_break_duration: Actual logged break duration in seconds
        user: User object to get company configuration

    Returns:
        tuple: (work_duration_in_seconds, effective_break_duration_in_seconds)
    """
    # Calculate raw duration
    raw_duration = (departure_time - arrival_time).total_seconds()

    # Get company work configuration for break rules
    company_config = CompanyWorkConfig.query.filter_by(company_id=user.company_id).first()
    if not company_config:
        # Use Germany defaults if no company config exists
        preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)  # Note: Germany has specific labor laws
        break_threshold_hours = preset['break_after_hours']
        mandatory_break_minutes = preset['break_duration_minutes']
        # REMOVED: additional_break_threshold_hours = preset['additional_break_threshold_hours']  # This field no longer exists in the model
        # REMOVED: additional_break_minutes = preset['additional_break_minutes']  # This field no longer exists in the model
    else:
        break_threshold_hours = company_config.break_after_hours
        mandatory_break_minutes = company_config.break_duration_minutes
        # REMOVED: additional_break_threshold_hours = company_config.additional_break_threshold_hours  # This field no longer exists in the model
        # REMOVED: additional_break_minutes = company_config.additional_break_minutes  # This field no longer exists in the model

    # Calculate mandatory breaks based on work duration
    work_hours = raw_duration / 3600  # Convert seconds to hours
    configured_break_seconds = 0

    # Apply primary break if work duration exceeds threshold
    if work_hours > break_threshold_hours:
        configured_break_seconds += mandatory_break_minutes * 60

    # Apply additional break if work duration exceeds additional threshold
    # REMOVED: if work_hours > additional_break_threshold_hours:  # This field no longer exists in the model
        # REMOVED: configured_break_seconds += additional_break_minutes * 60  # This field no longer exists in the model

    # Use the greater of configured breaks or actual logged breaks
    effective_break_duration = max(configured_break_seconds, total_break_duration)

    # Calculate final work duration
    work_duration = int(raw_duration - effective_break_duration)

    return work_duration, effective_break_duration

@app.route('/api/resume/<int:entry_id>', methods=['POST'])
@login_required
def resume_entry(entry_id):
    # Find the entry to resume for the current user
    entry_to_resume = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()

    # Check if the entry is from today
    today = datetime.now().date()
    if entry_to_resume.arrival_time.date() < today:
        return jsonify({
            'success': False,
            'message': 'Cannot resume entries from previous days.'
        }), 400

    # Check if there's already an active entry
    active_entry = TimeEntry.query.filter_by(user_id=session['user_id'], departure_time=None).first()
    if active_entry:
        return jsonify({
            'success': False,
            'message': 'Cannot resume this entry. Another session is already active.'
        }), 400

    # Clear the departure time to make this entry active again
    entry_to_resume.departure_time = None

    # Reset pause state if it was paused
    entry_to_resume.is_paused = False
    entry_to_resume.pause_start_time = None

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Work resumed on existing entry',
        'id': entry_to_resume.id,
        'arrival_time': entry_to_resume.arrival_time.isoformat(),
        'total_break_duration': entry_to_resume.total_break_duration
    })

@app.route('/api/manual-entry', methods=['POST'])
@login_required
def manual_entry():
    try:
        data = request.get_json()

        # Extract data from request
        project_id = data.get('project_id')
        start_date = data.get('start_date')
        start_time = data.get('start_time')
        end_date = data.get('end_date')
        end_time = data.get('end_time')
        break_minutes = int(data.get('break_minutes', 0))
        notes = data.get('notes', '')

        # Validate required fields
        if not all([start_date, start_time, end_date, end_time]):
            return jsonify({'error': 'Start and end date/time are required'}), 400

        # Parse datetime strings
        try:
            arrival_datetime = datetime.strptime(f"{start_date} {start_time}", '%Y-%m-%d %H:%M:%S')
            departure_datetime = datetime.strptime(f"{end_date} {end_time}", '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try without seconds if parsing fails
                arrival_datetime = datetime.strptime(f"{start_date} {start_time}:00", '%Y-%m-%d %H:%M:%S')
                departure_datetime = datetime.strptime(f"{end_date} {end_time}:00", '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return jsonify({'error': 'Invalid date/time format'}), 400

        # Validate that end time is after start time
        if departure_datetime <= arrival_datetime:
            return jsonify({'error': 'End time must be after start time'}), 400

        # Apply time rounding if enabled
        rounded_arrival, rounded_departure = apply_time_rounding(arrival_datetime, departure_datetime, g.user)

        # Validate project access if project is specified
        if project_id:
            project = Project.query.get(project_id)
            if not project or not project.is_user_allowed(g.user):
                return jsonify({'error': 'Invalid or unauthorized project'}), 403

        # Check for overlapping entries for this user (using rounded times)
        overlapping_entry = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            TimeEntry.departure_time.isnot(None),
            TimeEntry.arrival_time < rounded_departure,
            TimeEntry.departure_time > rounded_arrival
        ).first()

        if overlapping_entry:
            return jsonify({
                'error': 'This time entry overlaps with an existing entry'
            }), 400

        # Calculate total duration in seconds (using rounded times)
        total_duration = int((rounded_departure - rounded_arrival).total_seconds())
        break_duration_seconds = break_minutes * 60

        # Apply rounding to break duration if enabled
        interval_minutes, round_to_nearest = get_user_rounding_settings(g.user)
        if interval_minutes > 0:
            break_duration_seconds = round_duration_to_interval(
                break_duration_seconds, interval_minutes, round_to_nearest
            )

        # Validate break duration doesn't exceed total duration
        if break_duration_seconds >= total_duration:
            return jsonify({'error': 'Break duration cannot exceed total work duration'}), 400

        # Calculate work duration (total duration minus breaks)
        work_duration = total_duration - break_duration_seconds

        # Create the manual time entry (using rounded times)
        new_entry = TimeEntry(
            user_id=g.user.id,
            arrival_time=rounded_arrival,
            departure_time=rounded_departure,
            duration=work_duration,
            total_break_duration=break_duration_seconds,
            project_id=int(project_id) if project_id else None,
            notes=notes,
            is_paused=False,
            pause_start_time=None
        )

        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Manual time entry added successfully',
            'entry_id': new_entry.id
        })

    except Exception as e:
        logger.error(f"Error creating manual time entry: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the time entry'}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/test')
def test():
    return "App is working!"

# system_admin routes moved to system_admin blueprint

@app.route('/system-admin/settings', methods=['GET', 'POST'])
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
        return redirect(url_for('system_admin_settings'))

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

# system_admin_branding moved to system_admin blueprint

@app.route('/system-admin/health')
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
    from datetime import datetime, timedelta
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
                         today_events=today_events)

# Company Management Routes
# Export routes moved to routes/export.py


@app.route('/analytics')
@app.route('/analytics/<mode>')
@login_required
def analytics(mode='personal'):
    """Unified analytics view combining history, team hours, and graphs"""
    # Validate mode parameter
    if mode not in ['personal', 'team']:
        mode = 'personal'

    # Check team access for team mode
    if mode == 'team':
        if not g.user.team_id:
            flash('You must be assigned to a team to view team analytics.', 'warning')
            return redirect(url_for('analytics', mode='personal'))

        if g.user.role not in [Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]:
            flash('You do not have permission to view team analytics.', 'error')
            return redirect(url_for('analytics', mode='personal'))

    # Get available projects for filtering
    available_projects = []
    all_projects = Project.query.filter_by(is_active=True).all()
    for project in all_projects:
        if project.is_user_allowed(g.user):
            available_projects.append(project)

    # Get team members if in team mode
    team_members = []
    if mode == 'team' and g.user.team_id:
        team_members = User.query.filter_by(team_id=g.user.team_id).all()

    # Default date range (current week)
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    return render_template('analytics.html',
                         title='Time Analytics',
                         mode=mode,
                         available_projects=available_projects,
                         team_members=team_members,
                         default_start_date=start_of_week.strftime('%Y-%m-%d'),
                         default_end_date=end_of_week.strftime('%Y-%m-%d'))

@app.route('/api/analytics/data')
@login_required
def analytics_data():
    """API endpoint for analytics data"""
    mode = request.args.get('mode', 'personal')
    view_type = request.args.get('view', 'table')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    project_filter = request.args.get('project_id')
    granularity = request.args.get('granularity', 'daily')

    # Validate mode
    if mode not in ['personal', 'team']:
        return jsonify({'error': 'Invalid mode'}), 400

    # Check permissions for team mode
    if mode == 'team':
        if not g.user.team_id:
            return jsonify({'error': 'No team assigned'}), 403
        if g.user.role not in [Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]:
            return jsonify({'error': 'Insufficient permissions'}), 403

    try:
        # Parse dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get filtered data
        data = get_filtered_analytics_data(g.user, mode, start_date, end_date, project_filter)

        # Format data based on view type
        if view_type == 'graph':
            formatted_data = format_graph_data(data, granularity)
            # For burndown chart, we need task data instead of time entries
            chart_type = request.args.get('chart_type', 'timeSeries')
            if chart_type == 'burndown':
                # Get tasks for burndown chart
                tasks = get_filtered_tasks_for_burndown(g.user, mode, start_date, end_date, project_filter)
                burndown_data = format_burndown_data(tasks, start_date, end_date)
                formatted_data.update(burndown_data)
        elif view_type == 'team':
            formatted_data = format_team_data(data, granularity)
        else:
            formatted_data = format_table_data(data)

        return jsonify(formatted_data)

    except Exception as e:
        logger.error(f"Error in analytics_data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# get_filtered_analytics_data moved to routes/export_api.py


@app.route('/api/system-admin/stats')
@system_admin_required
def api_system_admin_stats():
    """API: Get real-time system statistics for dashboard"""
    from datetime import datetime, timedelta

    # Get basic counts
    total_companies = Company.query.count()
    total_users = User.query.count()
    total_teams = Team.query.count()
    total_projects = Project.query.count()
    total_time_entries = TimeEntry.query.count()

    # Active sessions
    active_sessions = TimeEntry.query.filter_by(departure_time=None, is_paused=False).count()
    paused_sessions = TimeEntry.query.filter_by(is_paused=True).count()

    # Recent activity (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_users = User.query.filter(User.created_at >= yesterday).count()
    recent_companies = Company.query.filter(Company.created_at >= yesterday).count()
    recent_time_entries = TimeEntry.query.filter(TimeEntry.arrival_time >= yesterday).count()

    # System health
    orphaned_users = User.query.filter_by(company_id=None).count()
    orphaned_time_entries = TimeEntry.query.filter_by(user_id=None).count()
    blocked_users = User.query.filter_by(is_blocked=True).count()
    unverified_users = User.query.filter_by(is_verified=False).count()

    return jsonify({
        'totals': {
            'companies': total_companies,
            'users': total_users,
            'teams': total_teams,
            'projects': total_projects,
            'time_entries': total_time_entries
        },
        'active': {
            'sessions': active_sessions,
            'paused_sessions': paused_sessions
        },
        'recent': {
            'users': recent_users,
            'companies': recent_companies,
            'time_entries': recent_time_entries
        },
        'health': {
            'orphaned_users': orphaned_users,
            'orphaned_time_entries': orphaned_time_entries,
            'blocked_users': blocked_users,
            'unverified_users': unverified_users
        }
    })

@app.route('/api/system-admin/companies/<int:company_id>/users')
@app.route('/api/system-admin/users/<int:user_id>/toggle-block', methods=['POST'])
@app.route('/api/system-admin/companies/<int:company_id>/stats')
# Analytics export API moved to routes/export_api.py


# Dashboard API Endpoints
@app.route('/api/dashboard')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_dashboard():
    """Get user's dashboard configuration and widgets."""
    try:
        # Get or create user dashboard
        dashboard = UserDashboard.query.filter_by(user_id=g.user.id).first()
        if not dashboard:
            dashboard = UserDashboard(user_id=g.user.id)
            db.session.add(dashboard)
            db.session.commit()
            logger.info(f"Created new dashboard {dashboard.id} for user {g.user.id}")
        else:
            logger.info(f"Using existing dashboard {dashboard.id} for user {g.user.id}")

        # Get user's widgets
        widgets = DashboardWidget.query.filter_by(dashboard_id=dashboard.id).order_by(DashboardWidget.grid_y, DashboardWidget.grid_x).all()

        logger.info(f"Found {len(widgets)} widgets for dashboard {dashboard.id}")
        logger.info(f"Widget details: {[(w.id, w.widget_type.value, w.grid_x, w.grid_y) for w in widgets]}")

        # Convert to JSON format
        widget_data = []
        for widget in widgets:
            # Convert grid size to simple size names
            if widget.grid_width == 1 and widget.grid_height == 1:
                size = 'small'
            elif widget.grid_width == 2 and widget.grid_height == 1:
                size = 'medium'
            elif widget.grid_width == 2 and widget.grid_height == 2:
                size = 'large'
            elif widget.grid_width == 3 and widget.grid_height == 1:
                size = 'wide'
            else:
                size = 'small'

            # Parse config JSON
            try:
                import json
                config = json.loads(widget.config) if widget.config else {}
            except (json.JSONDecodeError, TypeError):
                config = {}

            widget_data.append({
                'id': widget.id,
                'type': widget.widget_type.value,
                'title': widget.title,
                'size': size,
                'grid_x': widget.grid_x,
                'grid_y': widget.grid_y,
                'grid_width': widget.grid_width,
                'grid_height': widget.grid_height,
                'config': config
            })

        return jsonify({
            'success': True,
            'dashboard': {
                'id': dashboard.id,
                'layout_config': dashboard.layout_config,
                'grid_columns': dashboard.grid_columns,
                'theme': dashboard.theme
            },
            'widgets': widget_data
        })

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/widgets', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def create_or_update_widget():
    """Create or update a dashboard widget."""
    try:
        data = request.get_json()

        # Get or create user dashboard
        dashboard = UserDashboard.query.filter_by(user_id=g.user.id).first()
        if not dashboard:
            dashboard = UserDashboard(user_id=g.user.id)
            db.session.add(dashboard)
            db.session.flush()  # Get the ID
            logger.info(f"Created new dashboard {dashboard.id} for user {g.user.id} in widget creation")
        else:
            logger.info(f"Using existing dashboard {dashboard.id} for user {g.user.id} in widget creation")

        # Check if updating existing widget
        widget_id = data.get('widget_id')
        if widget_id:
            widget = DashboardWidget.query.filter_by(
                id=widget_id,
                dashboard_id=dashboard.id
            ).first()
            if not widget:
                return jsonify({'success': False, 'error': 'Widget not found'})
        else:
            # Create new widget
            widget = DashboardWidget(dashboard_id=dashboard.id)
            # Find next available position
            max_y = db.session.query(func.max(DashboardWidget.grid_y)).filter_by(
                dashboard_id=dashboard.id
            ).scalar() or 0
            widget.grid_y = max_y + 1
            widget.grid_x = 0

        # Update widget properties
        widget.widget_type = WidgetType(data['type'])
        widget.title = data['title']

        # Convert size to grid dimensions
        size = data.get('size', 'small')
        if size == 'small':
            widget.grid_width = 1
            widget.grid_height = 1
        elif size == 'medium':
            widget.grid_width = 2
            widget.grid_height = 1
        elif size == 'large':
            widget.grid_width = 2
            widget.grid_height = 2
        elif size == 'wide':
            widget.grid_width = 3
            widget.grid_height = 1

        # Build config from form data
        config = {}
        for key, value in data.items():
            if key not in ['type', 'title', 'size', 'widget_id']:
                config[key] = value

        # Store config as JSON string
        if config:
            import json
            widget.config = json.dumps(config)
        else:
            widget.config = None

        if not widget_id:
            db.session.add(widget)
            logger.info(f"Creating new widget: {widget.widget_type.value} for dashboard {dashboard.id}")
        else:
            logger.info(f"Updating existing widget {widget_id}")

        db.session.commit()
        logger.info(f"Widget saved successfully with ID: {widget.id}")

        # Verify the widget was actually saved
        saved_widget = DashboardWidget.query.filter_by(id=widget.id).first()
        if saved_widget:
            logger.info(f"Verification: Widget {widget.id} exists in database with dashboard_id: {saved_widget.dashboard_id}")
        else:
            logger.error(f"Verification failed: Widget {widget.id} not found in database")

        # Convert grid size back to simple size name for response
        if widget.grid_width == 1 and widget.grid_height == 1:
            size_name = 'small'
        elif widget.grid_width == 2 and widget.grid_height == 1:
            size_name = 'medium'
        elif widget.grid_width == 2 and widget.grid_height == 2:
            size_name = 'large'
        elif widget.grid_width == 3 and widget.grid_height == 1:
            size_name = 'wide'
        else:
            size_name = 'small'

        # Parse config for response
        try:
            import json
            config_dict = json.loads(widget.config) if widget.config else {}
        except (json.JSONDecodeError, TypeError):
            config_dict = {}

        return jsonify({
            'success': True,
            'message': 'Widget saved successfully',
            'widget': {
                'id': widget.id,
                'type': widget.widget_type.value,
                'title': widget.title,
                'size': size_name,
                'grid_x': widget.grid_x,
                'grid_y': widget.grid_y,
                'grid_width': widget.grid_width,
                'grid_height': widget.grid_height,
                'config': config_dict
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving widget: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/widgets/<int:widget_id>', methods=['DELETE'])
@role_required(Role.TEAM_MEMBER)
@company_required
def delete_widget(widget_id):
    """Delete a dashboard widget."""
    try:
        # Get user dashboard
        dashboard = UserDashboard.query.filter_by(user_id=g.user.id).first()
        if not dashboard:
            return jsonify({'success': False, 'error': 'Dashboard not found'})

        # Find and delete widget
        widget = DashboardWidget.query.filter_by(
            id=widget_id,
            dashboard_id=dashboard.id
        ).first()

        if not widget:
            logger.error(f"Widget {widget_id} not found for dashboard {dashboard.id}")
            return jsonify({'success': False, 'error': 'Widget not found'})

        logger.info(f"Deleting widget {widget_id} of type {widget.widget_type.value} from dashboard {dashboard.id}")

        # Log all widgets before deletion
        all_widgets = DashboardWidget.query.filter_by(dashboard_id=dashboard.id).all()
        logger.info(f"Widgets before deletion: {[(w.id, w.widget_type.value) for w in all_widgets]}")

        # No need to update positions for grid-based layout

        db.session.delete(widget)
        db.session.commit()

        # Log all widgets after deletion
        remaining_widgets = DashboardWidget.query.filter_by(dashboard_id=dashboard.id).all()
        logger.info(f"Widgets after deletion: {[(w.id, w.widget_type.value) for w in remaining_widgets]}")

        return jsonify({'success': True, 'message': 'Widget deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting widget: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/positions', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_widget_positions():
    """Update widget grid positions after drag and drop."""
    try:
        data = request.get_json()
        positions = data.get('positions', [])

        # Get user dashboard
        dashboard = UserDashboard.query.filter_by(user_id=g.user.id).first()
        if not dashboard:
            return jsonify({'success': False, 'error': 'Dashboard not found'})

        # Update grid positions
        for pos_data in positions:
            widget = DashboardWidget.query.filter_by(
                id=pos_data['id'],
                dashboard_id=dashboard.id
            ).first()
            if widget:
                # For now, just assign sequential grid positions
                # In a more advanced implementation, we'd calculate actual grid coordinates
                widget.grid_x = pos_data.get('grid_x', 0)
                widget.grid_y = pos_data.get('grid_y', pos_data.get('position', 0))

        db.session.commit()

        return jsonify({'success': True, 'message': 'Positions updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating positions: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Widget data endpoints
@app.route('/api/dashboard/widgets/<int:widget_id>/data')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_widget_data(widget_id):
    """Get data for a specific widget."""
    try:
        # Get user dashboard
        dashboard = UserDashboard.query.filter_by(user_id=g.user.id).first()
        if not dashboard:
            return jsonify({'success': False, 'error': 'Dashboard not found'})

        # Find widget
        widget = DashboardWidget.query.filter_by(
            id=widget_id,
            dashboard_id=dashboard.id
        ).first()

        if not widget:
            return jsonify({'success': False, 'error': 'Widget not found'})

        # Get widget-specific data based on type
        widget_data = {}

        if widget.widget_type == WidgetType.DAILY_SUMMARY:
            from datetime import datetime, timedelta

            config = widget.config or {}
            period = config.get('summary_period', 'daily')

            # Calculate time summaries
            now = datetime.now()

            # Today's summary
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_entries = TimeEntry.query.filter(
                TimeEntry.user_id == g.user.id,
                TimeEntry.arrival_time >= start_of_today,
                TimeEntry.departure_time.isnot(None)
            ).all()
            today_seconds = sum(entry.duration or 0 for entry in today_entries)

            # This week's summary
            start_of_week = start_of_today - timedelta(days=start_of_today.weekday())
            week_entries = TimeEntry.query.filter(
                TimeEntry.user_id == g.user.id,
                TimeEntry.arrival_time >= start_of_week,
                TimeEntry.departure_time.isnot(None)
            ).all()
            week_seconds = sum(entry.duration or 0 for entry in week_entries)

            # This month's summary
            start_of_month = start_of_today.replace(day=1)
            month_entries = TimeEntry.query.filter(
                TimeEntry.user_id == g.user.id,
                TimeEntry.arrival_time >= start_of_month,
                TimeEntry.departure_time.isnot(None)
            ).all()
            month_seconds = sum(entry.duration or 0 for entry in month_entries)

            widget_data.update({
                'today': f"{today_seconds // 3600}h {(today_seconds % 3600) // 60}m",
                'week': f"{week_seconds // 3600}h {(week_seconds % 3600) // 60}m",
                'month': f"{month_seconds // 3600}h {(month_seconds % 3600) // 60}m",
                'entries_today': len(today_entries),
                'entries_week': len(week_entries),
                'entries_month': len(month_entries)
            })

        elif widget.widget_type == WidgetType.ACTIVE_PROJECTS:
            config = widget.config or {}
            project_filter = config.get('project_filter', 'all')
            max_projects = int(config.get('max_projects', 5))

            # Get user's projects
            if g.user.role in [Role.ADMIN, Role.SUPERVISOR]:
                projects = Project.query.filter_by(
                    company_id=g.user.company_id,
                    is_active=True
                ).limit(max_projects).all()
            elif g.user.team_id:
                projects = Project.query.filter(
                    Project.company_id == g.user.company_id,
                    Project.is_active == True,
                    db.or_(Project.team_id == g.user.team_id, Project.team_id == None)
                ).limit(max_projects).all()
            else:
                projects = []

            widget_data['projects'] = [{
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'description': p.description
            } for p in projects]

        elif widget.widget_type == WidgetType.ASSIGNED_TASKS:
            config = widget.config or {}
            task_filter = config.get('task_filter', 'assigned')
            task_status = config.get('task_status', 'active')

            # Get user's tasks based on filter
            if task_filter == 'assigned':
                tasks = Task.query.filter_by(assigned_to_id=g.user.id)
            elif task_filter == 'created':
                # Filter by created tasks - using assigned_to as fallback since created_by_id was removed
                tasks = Task.query.filter_by(assigned_to_id=g.user.id)
            else:
                # Get tasks from user's projects
                if g.user.team_id:
                    project_ids = [p.id for p in Project.query.filter(
                        Project.company_id == g.user.company_id,
                        db.or_(Project.team_id == g.user.team_id, Project.team_id == None)
                    ).all()]
                    tasks = Task.query.filter(Task.project_id.in_(project_ids))
                else:
                    tasks = Task.query.join(Project).filter(Project.company_id == g.user.company_id)

            # Filter by status if specified
            if task_status != 'all':
                if task_status == 'active':
                    tasks = tasks.filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
                elif task_status == 'pending':
                    tasks = tasks.filter_by(status=TaskStatus.PENDING)
                elif task_status == 'completed':
                    tasks = tasks.filter_by(status=TaskStatus.COMPLETED)

            tasks = tasks.limit(10).all()

            widget_data['tasks'] = [{
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'status': t.status.value if t.status else 'Pending',
                'priority': t.priority.value if t.priority else 'Medium',
                'project_name': t.project.name if t.project else 'No Project'
            } for t in tasks]

        elif widget.widget_type == WidgetType.WEEKLY_CHART:
            from datetime import datetime, timedelta

            # Get weekly data for chart
            now = datetime.now()
            start_of_week = now - timedelta(days=now.weekday())

            weekly_data = []
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                day_entries = TimeEntry.query.filter(
                    TimeEntry.user_id == g.user.id,
                    TimeEntry.arrival_time >= day_start,
                    TimeEntry.arrival_time < day_end,
                    TimeEntry.departure_time.isnot(None)
                ).all()

                total_seconds = sum(entry.duration or 0 for entry in day_entries)
                weekly_data.append({
                    'day': day.strftime('%A'),
                    'date': day.strftime('%Y-%m-%d'),
                    'hours': round(total_seconds / 3600, 2),
                    'entries': len(day_entries)
                })

            widget_data['weekly_data'] = weekly_data

        elif widget.widget_type == WidgetType.TASK_PRIORITY:
            # Get tasks by priority
            if g.user.team_id:
                project_ids = [p.id for p in Project.query.filter(
                    Project.company_id == g.user.company_id,
                    db.or_(Project.team_id == g.user.team_id, Project.team_id == None)
                ).all()]
                tasks = Task.query.filter(
                    Task.project_id.in_(project_ids),
                    Task.assigned_to_id == g.user.id
                ).order_by(Task.priority.desc(), Task.created_at.desc()).limit(10).all()
            else:
                tasks = Task.query.filter_by(assigned_to_id=g.user.id).order_by(
                    Task.priority.desc(), Task.created_at.desc()
                ).limit(10).all()

            widget_data['priority_tasks'] = [{
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'priority': t.priority.value if t.priority else 'Medium',
                'status': t.status.value if t.status else 'Pending',
                'project_name': t.project.name if t.project else 'No Project'
            } for t in tasks]

        elif widget.widget_type == WidgetType.PROJECT_PROGRESS:
            # Get project progress data
            if g.user.role in [Role.ADMIN, Role.SUPERVISOR]:
                projects = Project.query.filter_by(
                    company_id=g.user.company_id,
                    is_active=True
                ).limit(5).all()
            elif g.user.team_id:
                projects = Project.query.filter(
                    Project.company_id == g.user.company_id,
                    Project.is_active == True,
                    db.or_(Project.team_id == g.user.team_id, Project.team_id == None)
                ).limit(5).all()
            else:
                projects = []

            project_progress = []
            for project in projects:
                total_tasks = Task.query.filter_by(project_id=project.id).count()
                completed_tasks = Task.query.filter_by(
                    project_id=project.id,
                    status=TaskStatus.COMPLETED
                ).count()

                progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                project_progress.append({
                    'id': project.id,
                    'name': project.name,
                    'code': project.code,
                    'progress': round(progress, 1),
                    'completed_tasks': completed_tasks,
                    'total_tasks': total_tasks
                })

            widget_data['project_progress'] = project_progress

        elif widget.widget_type == WidgetType.PRODUCTIVITY_METRICS:
            from datetime import datetime, timedelta

            # Calculate productivity metrics
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)

            # This week vs last week comparison
            this_week_entries = TimeEntry.query.filter(
                TimeEntry.user_id == g.user.id,
                TimeEntry.arrival_time >= week_ago,
                TimeEntry.departure_time.isnot(None)
            ).all()

            last_week_entries = TimeEntry.query.filter(
                TimeEntry.user_id == g.user.id,
                TimeEntry.arrival_time >= week_ago - timedelta(days=7),
                TimeEntry.arrival_time < week_ago,
                TimeEntry.departure_time.isnot(None)
            ).all()

            this_week_hours = sum(entry.duration or 0 for entry in this_week_entries) / 3600
            last_week_hours = sum(entry.duration or 0 for entry in last_week_entries) / 3600

            productivity_change = ((this_week_hours - last_week_hours) / last_week_hours * 100) if last_week_hours > 0 else 0

            widget_data.update({
                'this_week_hours': round(this_week_hours, 1),
                'last_week_hours': round(last_week_hours, 1),
                'productivity_change': round(productivity_change, 1),
                'avg_daily_hours': round(this_week_hours / 7, 1),
                'total_entries': len(this_week_entries)
            })

        return jsonify({
            'success': True,
            'data': widget_data
        })

    except Exception as e:
        logger.error(f"Error getting widget data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/current-timer-status')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_current_timer_status():
    """Get current timer status for dashboard widgets."""
    try:
        # Get the user's current active time entry
        active_entry = TimeEntry.query.filter_by(
            user_id=g.user.id,
            departure_time=None
        ).first()

        if active_entry:
            # Calculate current duration
            now = datetime.now()
            elapsed_seconds = int((now - active_entry.arrival_time).total_seconds())

            return jsonify({
                'success': True,
                'isActive': True,
                'startTime': active_entry.arrival_time.isoformat(),
                'currentDuration': elapsed_seconds,
                'entryId': active_entry.id
            })
        else:
            return jsonify({
                'success': True,
                'isActive': False,
                'message': 'No active timer'
            })

    except Exception as e:
        logger.error(f"Error getting timer status: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Smart Search API Endpoints
@app.route('/api/search/sprints')
@role_required(Role.TEAM_MEMBER)
@company_required
def search_sprints():
    """Search for sprints for smart search auto-completion"""
    try:
        query = request.args.get('q', '').strip()

        if not query:
            return jsonify({'success': True, 'sprints': []})

        # Search sprints in the same company
        sprints = Sprint.query.filter(
            Sprint.company_id == g.user.company_id,
            Sprint.name.ilike(f'%{query}%')
        ).limit(10).all()

        # Filter sprints user has access to
        accessible_sprints = [
            sprint for sprint in sprints
            if sprint.can_user_access(g.user)
        ]

        sprint_list = [
            {
                'id': sprint.id,
                'name': sprint.name,
                'status': sprint.status.value
            }
            for sprint in accessible_sprints
        ]

        return jsonify({'success': True, 'sprints': sprint_list})

    except Exception as e:
        logger.error(f"Error in search_sprints: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/render-markdown', methods=['POST'])
@login_required
def render_markdown():
    """Render markdown content to HTML for preview"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'html': '<p class="preview-placeholder">Start typing to see the preview...</p>'})
        
        # Parse frontmatter and extract body
        from frontmatter_utils import parse_frontmatter
        metadata, body = parse_frontmatter(content)
        
        # Render markdown to HTML
        try:
            import markdown
            # Use extensions for better markdown support
            html = markdown.markdown(body, extensions=['extra', 'codehilite', 'toc', 'tables', 'fenced_code'])
        except ImportError:
            # Fallback if markdown not installed
            html = f'<pre>{body}</pre>'
        
        return jsonify({'html': html})
        
    except Exception as e:
        logger.error(f"Error rendering markdown: {str(e)}")
        return jsonify({'html': '<p class="error">Error rendering markdown</p>'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)