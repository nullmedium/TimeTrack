from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, g, Response, send_file
from models import db, TimeEntry, WorkConfig, User, SystemSettings, Team, Role, Project, Company, CompanyWorkConfig, UserPreferences, WorkRegion, AccountType, ProjectCategory, Task, SubTask, TaskStatus, TaskPriority
from data_formatting import (
    format_duration, prepare_export_data, prepare_team_hours_export_data,
    format_table_data, format_graph_data, format_team_data
)
from data_export import (
    export_to_csv, export_to_excel, export_team_hours_to_csv, export_team_hours_to_excel,
    export_analytics_csv, export_analytics_excel
)
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
from werkzeug.security import check_password_hash

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/timetrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_timetrack')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts for 7 days

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.example.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@example.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'TimeTrack <noreply@timetrack.com>')

# Log mail configuration (without password)
logger.info(f"Mail server: {app.config['MAIL_SERVER']}")
logger.info(f"Mail port: {app.config['MAIL_PORT']}")
logger.info(f"Mail use TLS: {app.config['MAIL_USE_TLS']}")
logger.info(f"Mail username: {app.config['MAIL_USERNAME']}")
logger.info(f"Mail default sender: {app.config['MAIL_DEFAULT_SENDER']}")

mail = Mail(app)

# Initialize the database with the app
db.init_app(app)

# Consolidated migration using migrate_db module
def run_migrations():
    """Run all database migrations using the consolidated migrate_db module."""
    try:
        from migrate_db import run_all_migrations
        run_all_migrations()
        print("Database migrations completed successfully!")
    except ImportError as e:
        print(f"Error importing migrate_db: {e}")
        print("Falling back to basic table creation...")
        with app.app_context():
            db.create_all()
            init_system_settings()
    except Exception as e:
        print(f"Error during database migration: {e}")
        raise

def migrate_to_company_model():
    """Migrate existing data to support company model (stub - handled by migrate_db)"""
    try:
        from migrate_db import migrate_to_company_model, get_db_path
        db_path = get_db_path()
        migrate_to_company_model(db_path)
    except ImportError:
        print("migrate_db module not available - skipping company model migration")
    except Exception as e:
        print(f"Error during company migration: {e}")
        raise

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
        db.session.commit()

    if not SystemSettings.query.filter_by(key='email_verification_required').first():
        print("Adding email_verification_required system setting...")
        email_setting = SystemSettings(
            key='email_verification_required',
            value='true',
            description='Controls whether email verification is required for new user accounts'
        )
        db.session.add(email_setting)
        db.session.commit()

def migrate_data():
    """Handle data migrations and setup (stub - handled by migrate_db)"""
    try:
        from migrate_db import migrate_data
        migrate_data()
    except ImportError:
        print("migrate_db module not available - skipping data migration")
    except Exception as e:
        print(f"Error during data migration: {e}")
        raise

def migrate_work_config_data():
    """Migrate existing WorkConfig data to new architecture (stub - handled by migrate_db)"""
    try:
        from migrate_db import migrate_work_config_data, get_db_path
        db_path = get_db_path()
        migrate_work_config_data(db_path)
    except ImportError:
        print("migrate_db module not available - skipping work config data migration")
    except Exception as e:
        print(f"Error during work config migration: {e}")
        raise

def migrate_task_system():
    """Create tables for the task management system (stub - handled by migrate_db)"""
    try:
        from migrate_db import migrate_task_system, get_db_path
        db_path = get_db_path()
        migrate_task_system(db_path)
    except ImportError:
        print("migrate_db module not available - skipping task system migration")
    except Exception as e:
        print(f"Error during task system migration: {e}")
        raise

# Call this function during app initialization
@app.before_first_request
def initialize_app():
    run_migrations()  # This handles all migrations including work config data

# Add this after initializing the app but before defining routes
@app.context_processor
def inject_globals():
    """Make certain variables available to all templates."""
    return {
        'Role': Role,
        'AccountType': AccountType,
        'current_year': datetime.now().year
    }

# Template filters for date/time formatting
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
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Admin-only decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or (g.user.role != Role.ADMIN and g.user.role != Role.SYSTEM_ADMIN):
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# System Admin-only decorator
def system_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or g.user.role != Role.SYSTEM_ADMIN:
            flash('You need system administrator privileges to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def get_system_setting(key, default='false'):
    """Helper function to get system setting value"""
    setting = SystemSettings.query.filter_by(key=key).first()
    return setting.value if setting else default

def is_system_admin(user=None):
    """Helper function to check if user is system admin"""
    if user is None:
        user = g.user
    return user and user.role == Role.SYSTEM_ADMIN

def can_access_system_settings(user=None):
    """Helper function to check if user can access system-wide settings"""
    return is_system_admin(user)

def get_available_roles():
    """Get roles available for assignment, excluding SYSTEM_ADMIN unless one already exists"""
    roles = list(Role)

    # Only show SYSTEM_ADMIN role if at least one system admin already exists
    # This prevents accidental creation of system admins
    system_admin_exists = User.query.filter_by(role=Role.SYSTEM_ADMIN).count() > 0

    if not system_admin_exists:
        roles = [role for role in roles if role != Role.SYSTEM_ADMIN]

    return roles

# Add this decorator function after your existing decorators
def role_required(min_role):
    """
    Decorator to restrict access based on user role.
    min_role should be a Role enum value (e.g., Role.TEAM_LEADER)
    """
    def role_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                return redirect(url_for('login', next=request.url))

            # Admin and System Admin always have access
            if g.user.role == Role.ADMIN or g.user.role == Role.SYSTEM_ADMIN:
                return f(*args, **kwargs)

            # Check role hierarchy
            role_hierarchy = {
                Role.TEAM_MEMBER: 1,
                Role.TEAM_LEADER: 2,
                Role.SUPERVISOR: 3,
                Role.ADMIN: 4,
                Role.SYSTEM_ADMIN: 5
            }

            if role_hierarchy.get(g.user.role, 0) < role_hierarchy.get(min_role, 0):
                flash('You do not have sufficient permissions to access this page.', 'error')
                return redirect(url_for('home'))

            return f(*args, **kwargs)
        return decorated_function
    return role_decorator

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
            flash('Your company is not active. Please contact support.', 'error')
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function

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

            # Check if user is verified
            if not g.user.is_verified and request.endpoint not in ['verify_email', 'static', 'logout', 'setup_company']:
                # Allow unverified users to access only verification and static resources
                if request.endpoint not in ['login', 'register']:
                    flash('Please verify your email address before accessing this page.', 'warning')
                    session.clear()
                    return redirect(url_for('login'))
        else:
            g.company = None

@app.route('/')
def home():
    if g.user:
        # Get active entry (no departure time)
        active_entry = TimeEntry.query.filter_by(
            user_id=g.user.id,
            departure_time=None
        ).first()

        # Get today's completed entries for history
        today = datetime.now().date()
        history = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            TimeEntry.departure_time.isnot(None),
            TimeEntry.arrival_time >= datetime.combine(today, time.min),
            TimeEntry.arrival_time <= datetime.combine(today, time.max)
        ).order_by(TimeEntry.arrival_time.desc()).all()

        # Get available projects for this user (company-scoped)
        available_projects = []
        if g.user.company_id:
            all_projects = Project.query.filter_by(
                company_id=g.user.company_id,
                is_active=True
            ).all()
            for project in all_projects:
                if project.is_user_allowed(g.user):
                    available_projects.append(project)

        return render_template('index.html', title='Home',
                             active_entry=active_entry,
                             history=history,
                             available_projects=available_projects)
    else:
        return render_template('about.html', title='Home')

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

                    flash('Login successful!', 'success')
                    return redirect(url_for('home'))

        flash('Invalid username or password', 'error')

    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
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

    # Check if companies exist, if not redirect to company setup
    if Company.query.count() == 0:
        flash('No companies exist yet. Please set up your company first.', 'info')
        return redirect(url_for('setup_company'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        company_code = request.form.get('company_code', '').strip()

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not email:
            error = 'Email is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'
        elif not company_code:
            error = 'Company code is required'

        # Find company by code
        company = None
        if company_code:
            company = Company.query.filter_by(slug=company_code.lower()).first()
            if not company:
                error = 'Invalid company code'

        # Check for existing users within the company
        if company and not error:
            if User.query.filter_by(username=username, company_id=company.id).first():
                error = 'Username already exists in this company'
            elif User.query.filter_by(email=email, company_id=company.id).first():
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
                    msg = Message('Verify your TimeTrack account', recipients=[email])
                    msg.body = f'''Hello {username},

Thank you for registering with TimeTrack. To complete your registration, please click on the link below:

{verification_url}

This link will expire in 24 hours.

If you did not register for TimeTrack, please ignore this email.

Best regards,
The TimeTrack Team
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
        elif not email:
            error = 'Email is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'

        # Check for existing users globally (freelancers get unique usernames/emails)
        if not error:
            if User.query.filter_by(username=username).first():
                error = 'Username already exists'
            elif User.query.filter_by(email=email).first():
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

@app.route('/setup_company', methods=['GET', 'POST'])
def setup_company():
    """Company setup route for creating new companies with admin users"""
    existing_companies = Company.query.count()

    # Determine access level
    is_initial_setup = existing_companies == 0
    is_super_admin = g.user and g.user.role == Role.ADMIN and existing_companies > 0
    is_authorized = is_initial_setup or is_super_admin

    # Check authorization for non-initial setups
    if not is_initial_setup and not is_super_admin:
        flash('You do not have permission to create new companies.', 'error')
        return redirect(url_for('home') if g.user else url_for('login'))

    if request.method == 'POST':
        company_name = request.form.get('company_name')
        company_description = request.form.get('company_description', '')
        admin_username = request.form.get('admin_username')
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')
        confirm_password = request.form.get('confirm_password')

        # Validate input
        error = None
        if not company_name:
            error = 'Company name is required'
        elif not admin_username:
            error = 'Admin username is required'
        elif not admin_email:
            error = 'Admin email is required'
        elif not admin_password:
            error = 'Admin password is required'
        elif admin_password != confirm_password:
            error = 'Passwords do not match'
        elif len(admin_password) < 6:
            error = 'Password must be at least 6 characters long'

        if error is None:
            try:
                # Generate company slug
                import re
                slug = re.sub(r'[^\w\s-]', '', company_name.lower())
                slug = re.sub(r'[-\s]+', '-', slug).strip('-')

                # Ensure slug uniqueness
                base_slug = slug
                counter = 1
                while Company.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create company
                company = Company(
                    name=company_name,
                    slug=slug,
                    description=company_description,
                    is_active=True
                )
                db.session.add(company)
                db.session.flush()  # Get company.id without committing

                # Check if username/email already exists in this company context
                existing_user_by_username = User.query.filter_by(
                    username=admin_username,
                    company_id=company.id
                ).first()
                existing_user_by_email = User.query.filter_by(
                    email=admin_email,
                    company_id=company.id
                ).first()

                if existing_user_by_username:
                    error = 'Username already exists in this company'
                elif existing_user_by_email:
                    error = 'Email already registered in this company'

                if error is None:
                    # Create admin user
                    admin_user = User(
                        username=admin_username,
                        email=admin_email,
                        company_id=company.id,
                        role=Role.ADMIN,
                        is_verified=True  # Auto-verify company admin
                    )
                    admin_user.set_password(admin_password)
                    db.session.add(admin_user)
                    db.session.commit()

                    if is_initial_setup:
                        # Auto-login the admin user for initial setup
                        session['user_id'] = admin_user.id
                        session['username'] = admin_user.username
                        session['role'] = admin_user.role.value

                        flash(f'Company "{company_name}" created successfully! You are now logged in as the administrator.', 'success')
                        return redirect(url_for('home'))
                    else:
                        # For super admin creating additional companies, don't auto-login
                        flash(f'Company "{company_name}" created successfully! Admin user "{admin_username}" has been created with the company code "{slug}".', 'success')
                        return redirect(url_for('admin_company') if g.user else url_for('login'))
                else:
                    db.session.rollback()

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during company setup: {str(e)}")
                error = f"An error occurred during setup: {str(e)}"

        if error:
            flash(error, 'error')

    return render_template('setup_company.html',
                         title='Company Setup',
                         existing_companies=existing_companies,
                         is_initial_setup=is_initial_setup,
                         is_super_admin=is_super_admin)

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

@app.route('/dashboard')
@role_required(Role.TEAM_LEADER)
def dashboard():
    # Get dashboard data based on user role
    dashboard_data = {}

    if g.user.role == Role.ADMIN and g.user.company_id:
        # Admin sees everything within their company

        dashboard_data.update({
            'total_users': User.query.filter_by(company_id=g.user.company_id).count(),
            'total_teams': Team.query.filter_by(company_id=g.user.company_id).count(),
            'blocked_users': User.query.filter_by(company_id=g.user.company_id, is_blocked=True).count(),
            'unverified_users': User.query.filter_by(company_id=g.user.company_id, is_verified=False).count(),
            'recent_registrations': User.query.filter_by(company_id=g.user.company_id).order_by(User.id.desc()).limit(5).all()
        })

    if g.user.role in [Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]:

        # Team leaders and supervisors see team-related data
        if g.user.team_id or g.user.role == Role.ADMIN:
            if g.user.role == Role.ADMIN and g.user.company_id:
                # Admin can see all teams in their company
                teams = Team.query.filter_by(company_id=g.user.company_id).all()
                team_members = User.query.filter(
                    User.team_id.isnot(None),
                    User.company_id == g.user.company_id
                ).all()
            else:
                # Team leaders/supervisors see their own team
                teams = [Team.query.get(g.user.team_id)] if g.user.team_id else []

                team_members = User.query.filter_by(
                    team_id=g.user.team_id,
                    company_id=g.user.company_id
                ).all() if g.user.team_id else []

            dashboard_data.update({
                'teams': teams,
                'team_members': team_members,
                'team_member_count': len(team_members)
            })

    # Get recent time entries for the user's oversight
    if g.user.role == Role.ADMIN:
        # Admin sees all recent entries
        recent_entries = TimeEntry.query.order_by(TimeEntry.arrival_time.desc()).limit(10).all()
    elif g.user.team_id:
        # Team leaders see their team's entries
        team_user_ids = [user.id for user in User.query.filter_by(team_id=g.user.team_id).all()]
        recent_entries = TimeEntry.query.filter(TimeEntry.user_id.in_(team_user_ids)).order_by(TimeEntry.arrival_time.desc()).limit(10).all()
    else:
        recent_entries = []

    dashboard_data['recent_entries'] = recent_entries

    return render_template('dashboard.html', title='Dashboard', **dashboard_data)

# Redirect old admin dashboard URL to new dashboard

@app.route('/admin/users')
@admin_required
@company_required
def admin_users():
    users = User.query.filter_by(company_id=g.user.company_id).all()
    return render_template('admin_users.html', title='User Management', users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
@company_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        auto_verify = 'auto_verify' in request.form

        # Get role and team
        role_name = request.form.get('role')
        team_id = request.form.get('team_id')

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not email:
            error = 'Email is required'
        elif not password:
            error = 'Password is required'
        elif User.query.filter_by(username=username, company_id=g.user.company_id).first():
            error = 'Username already exists in your company'
        elif User.query.filter_by(email=email, company_id=g.user.company_id).first():
            error = 'Email already registered in your company'

        if error is None:
            # Convert role string to enum
            try:
                role = Role[role_name] if role_name else Role.TEAM_MEMBER
            except KeyError:
                role = Role.TEAM_MEMBER

            # Create new user with role and team
            new_user = User(
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
                msg = Message('Verify your TimeTrack account', recipients=[email])
                msg.body = f'''Hello {username},

An administrator has created an account for you on TimeTrack. To activate your account, please click on the link below:

{verification_url}

This link will expire in 24 hours.

Best regards,
The TimeTrack Team
'''
                mail.send(msg)

            db.session.add(new_user)
            db.session.commit()

            if auto_verify:
                flash(f'User {username} created and automatically verified!', 'success')
            else:
                flash(f'User {username} created! Verification email sent.', 'success')
            return redirect(url_for('admin_users'))

        flash(error, 'error')

    # Get all teams for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).all()
    roles = get_available_roles()

    return render_template('create_user.html', title='Create User', teams=teams, roles=roles)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def edit_user(user_id):
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Get role and team
        role_name = request.form.get('role')
        team_id = request.form.get('team_id')

        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not email:
            error = 'Email is required'
        elif username != user.username and User.query.filter_by(username=username, company_id=g.user.company_id).first():
            error = 'Username already exists in your company'
        elif email != user.email and User.query.filter_by(email=email, company_id=g.user.company_id).first():
            error = 'Email already registered in your company'
        if error is None:
            user.username = username
            user.email = email

            # Convert role string to enum
            try:
                user.role = Role[role_name] if role_name else Role.TEAM_MEMBER
            except KeyError:
                user.role = Role.TEAM_MEMBER

            user.team_id = team_id if team_id else None

            if password:
                user.set_password(password)

            db.session.commit()

            flash(f'User {username} updated successfully!', 'success')
            return redirect(url_for('admin_users'))

        flash(error, 'error')

    # Get all teams for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).all()
    roles = get_available_roles()

    return render_template('edit_user.html', title='Edit User', user=user, teams=teams, roles=roles)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
@company_required
def delete_user(user_id):
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()

    # Prevent deleting yourself
    if user.id == session.get('user_id'):
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'User {username} deleted successfully', 'success')
    return redirect(url_for('admin_users'))

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

        if error is None:
            user.email = email

            if new_password:
                user.set_password(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

        flash(error, 'error')

    return render_template('profile.html', title='My Profile', user=user)

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

    qr_uri = g.user.get_2fa_uri()
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

            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid verification code. Please try again.', 'error')

    return render_template('verify_2fa.html', title='Two-Factor Authentication')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

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
    # Get project and notes from request
    project_id = request.json.get('project_id') if request.json else None
    notes = request.json.get('notes') if request.json else None

    # Validate project access if project is specified
    if project_id:
        project = Project.query.get(project_id)
        if not project or not project.is_user_allowed(g.user):
            return jsonify({'error': 'Invalid or unauthorized project'}), 403

    # Create a new time entry with arrival time for the current user
    new_entry = TimeEntry(
        user_id=g.user.id,
        arrival_time=datetime.now(),
        project_id=int(project_id) if project_id else None,
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
        'arrival_time': entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S'),
        'departure_time': entry.departure_time.strftime('%Y-%m-%d %H:%M:%S'),
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

@app.route('/api/update/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()
    data = request.json

    if 'arrival_time' in data:
        try:
            entry.arrival_time = datetime.strptime(data['arrival_time'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid arrival time format'}), 400

    if 'departure_time' in data and data['departure_time']:
        try:
            entry.departure_time = datetime.strptime(data['departure_time'], '%Y-%m-%d %H:%M:%S')
            # Recalculate duration if both times are present
            if entry.arrival_time and entry.departure_time:
                # Calculate work duration considering breaks
                entry.duration, _ = calculate_work_duration(
                    entry.arrival_time,
                    entry.departure_time,
                    entry.total_break_duration,
                    g.user
                )
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid departure time format'}), 400

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Entry updated successfully',
        'entry': {
            'id': entry.id,
            'arrival_time': entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S'),
            'departure_time': entry.departure_time.strftime('%Y-%m-%d %H:%M:%S') if entry.departure_time else None,
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
        preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
        break_threshold_hours = preset['break_threshold_hours']
        mandatory_break_minutes = preset['mandatory_break_minutes']
        additional_break_threshold_hours = preset['additional_break_threshold_hours']
        additional_break_minutes = preset['additional_break_minutes']
    else:
        break_threshold_hours = company_config.break_threshold_hours
        mandatory_break_minutes = company_config.mandatory_break_minutes
        additional_break_threshold_hours = company_config.additional_break_threshold_hours
        additional_break_minutes = company_config.additional_break_minutes

    # Calculate mandatory breaks based on work duration
    work_hours = raw_duration / 3600  # Convert seconds to hours
    configured_break_seconds = 0

    # Apply primary break if work duration exceeds threshold
    if work_hours > break_threshold_hours:
        configured_break_seconds += mandatory_break_minutes * 60

    # Apply additional break if work duration exceeds additional threshold
    if work_hours > additional_break_threshold_hours:
        configured_break_seconds += additional_break_minutes * 60

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
        'arrival_time': entry_to_resume.arrival_time.strftime('%Y-%m-%d %H:%M:%S'),
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

@app.route('/admin/users/toggle-status/<int:user_id>')
@admin_required
@company_required
def toggle_user_status(user_id):
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()

    # Prevent blocking yourself
    if user.id == session.get('user_id'):
        flash('You cannot block your own account', 'error')
        return redirect(url_for('admin_users'))

    # Toggle the blocked status
    user.is_blocked = not user.is_blocked
    db.session.commit()

    if user.is_blocked:
        flash(f'User {user.username} has been blocked', 'success')
    else:
        flash(f'User {user.username} has been unblocked', 'success')

    return redirect(url_for('admin_users'))

# Add this route to manage system settings
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        # Update registration setting
        registration_enabled = 'registration_enabled' in request.form
        reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
        if reg_setting:
            reg_setting.value = 'true' if registration_enabled else 'false'

        # Update email verification setting
        email_verification_required = 'email_verification_required' in request.form
        email_setting = SystemSettings.query.filter_by(key='email_verification_required').first()
        if email_setting:
            email_setting.value = 'true' if email_verification_required else 'false'

        db.session.commit()
        flash('System settings updated successfully!', 'success')

    # Get current settings
    settings = {}
    for setting in SystemSettings.query.all():
        if setting.key == 'registration_enabled':
            settings['registration_enabled'] = setting.value == 'true'
        elif setting.key == 'email_verification_required':
            settings['email_verification_required'] = setting.value == 'true'

    return render_template('admin_settings.html', title='System Settings', settings=settings)

@app.route('/system-admin/dashboard')
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
    from datetime import datetime, timedelta
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

@app.route('/system-admin/users')
@system_admin_required
def system_admin_users():
    """System Admin: View all users across all companies"""
    filter_type = request.args.get('filter', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Build query based on filter
    query = User.query

    if filter_type == 'blocked':
        query = query.filter_by(is_blocked=True)
    elif filter_type == 'system_admins':
        query = query.filter_by(role=Role.SYSTEM_ADMIN)
    elif filter_type == 'admins':
        query = query.filter_by(role=Role.ADMIN)
    elif filter_type == 'unverified':
        query = query.filter_by(is_verified=False)
    elif filter_type == 'freelancers':
        query = query.filter_by(account_type=AccountType.FREELANCER)

    # Add company join for display
    query = query.join(Company).add_columns(Company.name.label('company_name'))

    # Order by creation date (newest first)
    query = query.order_by(User.created_at.desc())

    # Paginate results
    users = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('system_admin_users.html',
                         title='System Admin - All Users',
                         users=users,
                         current_filter=filter_type)

@app.route('/system-admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@system_admin_required
def system_admin_edit_user(user_id):
    """System Admin: Edit any user across companies"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        is_blocked = request.form.get('is_blocked') == 'on'
        is_verified = request.form.get('is_verified') == 'on'
        company_id = request.form.get('company_id')
        team_id = request.form.get('team_id') or None

        # Validation
        error = None

        # Check if username is unique within the company
        existing_user = User.query.filter(
            User.username == username,
            User.company_id == company_id,
            User.id != user_id
        ).first()

        if existing_user:
            error = f'Username "{username}" is already taken in this company.'

        # Check if email is unique within the company
        existing_email = User.query.filter(
            User.email == email,
            User.company_id == company_id,
            User.id != user_id
        ).first()

        if existing_email:
            error = f'Email "{email}" is already registered in this company.'

        if not error:
            # Update user
            user.username = username
            user.email = email
            user.role = Role(role)
            user.is_blocked = is_blocked
            user.is_verified = is_verified
            user.company_id = company_id
            user.team_id = team_id

            db.session.commit()
            flash(f'User {username} updated successfully.', 'success')
            return redirect(url_for('system_admin_users'))

        flash(error, 'error')

    # Get all companies and teams for form dropdowns
    companies = Company.query.order_by(Company.name).all()
    teams = Team.query.filter_by(company_id=user.company_id).order_by(Team.name).all()
    roles = get_available_roles()

    return render_template('system_admin_edit_user.html',
                         title=f'Edit User: {user.username}',
                         user=user,
                         companies=companies,
                         teams=teams,
                         roles=roles)

@app.route('/system-admin/users/<int:user_id>/delete', methods=['POST'])
@system_admin_required
def system_admin_delete_user(user_id):
    """System Admin: Delete any user (with safety checks)"""
    user = User.query.get_or_404(user_id)

    # Safety check: prevent deleting the last system admin
    if user.role == Role.SYSTEM_ADMIN:
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN).count()
        if system_admin_count <= 1:
            flash('Cannot delete the last system administrator.', 'error')
            return redirect(url_for('system_admin_users'))

    # Safety check: prevent deleting yourself
    if user.id == g.user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('system_admin_users'))

    username = user.username
    company_name = user.company.name if user.company else 'Unknown'

    # Delete related data first
    TimeEntry.query.filter_by(user_id=user.id).delete()
    WorkConfig.query.filter_by(user_id=user.id).delete()

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    flash(f'User "{username}" from company "{company_name}" has been deleted.', 'success')
    return redirect(url_for('system_admin_users'))

@app.route('/system-admin/companies')
@system_admin_required
def system_admin_companies():
    """System Admin: View all companies"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    companies = Company.query.order_by(Company.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    # Get user counts for each company
    company_stats = {}
    for company in companies.items:
        user_count = User.query.filter_by(company_id=company.id).count()
        admin_count = User.query.filter(
            User.company_id == company.id,
            User.role.in_([Role.ADMIN, Role.SYSTEM_ADMIN])
        ).count()
        company_stats[company.id] = {
            'user_count': user_count,
            'admin_count': admin_count
        }

    return render_template('system_admin_companies.html',
                         title='System Admin - All Companies',
                         companies=companies,
                         company_stats=company_stats)

@app.route('/system-admin/companies/<int:company_id>')
@system_admin_required
def system_admin_company_detail(company_id):
    """System Admin: View detailed company information"""
    company = Company.query.get_or_404(company_id)

    # Get company statistics
    users = User.query.filter_by(company_id=company.id).all()
    teams = Team.query.filter_by(company_id=company.id).all()
    projects = Project.query.filter_by(company_id=company.id).all()

    # Recent activity
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    recent_time_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= week_ago
    ).count()

    # Role distribution
    role_counts = {}
    for role in Role:
        count = User.query.filter_by(company_id=company.id, role=role).count()
        if count > 0:
            role_counts[role.value] = count

    return render_template('system_admin_company_detail.html',
                         title=f'Company: {company.name}',
                         company=company,
                         users=users,
                         teams=teams,
                         projects=projects,
                         recent_time_entries=recent_time_entries,
                         role_counts=role_counts)

@app.route('/system-admin/time-entries')
@system_admin_required
def system_admin_time_entries():
    """System Admin: View time entries across all companies"""
    page = request.args.get('page', 1, type=int)
    company_filter = request.args.get('company', '')
    per_page = 50

    # Build query
    query = TimeEntry.query.join(User).join(Company)

    if company_filter:
        query = query.filter(Company.id == company_filter)

    # Add columns for display
    query = query.add_columns(
        User.username,
        Company.name.label('company_name'),
        Project.name.label('project_name')
    ).outerjoin(Project)

    # Order by arrival time (newest first)
    query = query.order_by(TimeEntry.arrival_time.desc())

    # Paginate
    entries = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get companies for filter dropdown
    companies = Company.query.order_by(Company.name).all()

    return render_template('system_admin_time_entries.html',
                         title='System Admin - Time Entries',
                         entries=entries,
                         companies=companies,
                         current_company=company_filter)

@app.route('/system-admin/settings', methods=['GET', 'POST'])
@system_admin_required
def system_admin_settings():
    """System Admin: Global system settings"""
    if request.method == 'POST':
        # Update system settings
        registration_enabled = request.form.get('registration_enabled') == 'on'
        email_verification = request.form.get('email_verification_required') == 'on'

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

@app.route('/admin/work-policies', methods=['GET', 'POST'])
@admin_required
@company_required
def admin_work_policies():
    # Get or create company work config
    work_config = CompanyWorkConfig.query.filter_by(company_id=g.user.company_id).first()
    if not work_config:
        # Create default config for the company
        preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
        work_config = CompanyWorkConfig(
            company_id=g.user.company_id,
            work_hours_per_day=preset['work_hours_per_day'],
            mandatory_break_minutes=preset['mandatory_break_minutes'],
            break_threshold_hours=preset['break_threshold_hours'],
            additional_break_minutes=preset['additional_break_minutes'],
            additional_break_threshold_hours=preset['additional_break_threshold_hours'],
            region=WorkRegion.GERMANY,
            region_name=preset['region_name'],
            created_by_id=g.user.id
        )
        db.session.add(work_config)
        db.session.commit()

    if request.method == 'POST':
        try:
            # Handle regional preset selection
            if request.form.get('action') == 'apply_preset':
                region_code = request.form.get('region_preset')
                if region_code:
                    region = WorkRegion(region_code)
                    preset = CompanyWorkConfig.get_regional_preset(region)

                    work_config.work_hours_per_day = preset['work_hours_per_day']
                    work_config.mandatory_break_minutes = preset['mandatory_break_minutes']
                    work_config.break_threshold_hours = preset['break_threshold_hours']
                    work_config.additional_break_minutes = preset['additional_break_minutes']
                    work_config.additional_break_threshold_hours = preset['additional_break_threshold_hours']
                    work_config.region = region
                    work_config.region_name = preset['region_name']

                    db.session.commit()
                    flash(f'Applied {preset["region_name"]} work policy preset', 'success')
                    return redirect(url_for('admin_work_policies'))

            # Handle manual configuration update
            else:
                work_config.work_hours_per_day = float(request.form.get('work_hours_per_day', 8.0))
                work_config.mandatory_break_minutes = int(request.form.get('mandatory_break_minutes', 30))
                work_config.break_threshold_hours = float(request.form.get('break_threshold_hours', 6.0))
                work_config.additional_break_minutes = int(request.form.get('additional_break_minutes', 15))
                work_config.additional_break_threshold_hours = float(request.form.get('additional_break_threshold_hours', 9.0))
                work_config.region = WorkRegion.CUSTOM
                work_config.region_name = 'Custom Configuration'

                db.session.commit()
                flash('Work policies updated successfully!', 'success')
                return redirect(url_for('admin_work_policies'))

        except ValueError:
            flash('Please enter valid numbers for all fields', 'error')

    # Get available regional presets
    regional_presets = []
    for region in WorkRegion:
        preset = CompanyWorkConfig.get_regional_preset(region)
        regional_presets.append({
            'code': region.value,
            'name': preset['region_name'],
            'description': f"{preset['work_hours_per_day']}h/day, {preset['mandatory_break_minutes']}min break after {preset['break_threshold_hours']}h"
        })

    return render_template('admin_work_policies.html',
                         title='Work Policies',
                         work_config=work_config,
                         regional_presets=regional_presets,
                         WorkRegion=WorkRegion)

# Company Management Routes
@app.route('/admin/company')
@admin_required
@company_required
def admin_company():
    """View and manage company settings"""
    company = g.company

    # Get company statistics
    stats = {
        'total_users': User.query.filter_by(company_id=company.id).count(),
        'total_teams': Team.query.filter_by(company_id=company.id).count(),
        'total_projects': Project.query.filter_by(company_id=company.id).count(),
        'active_projects': Project.query.filter_by(company_id=company.id, is_active=True).count(),
    }

    return render_template('admin_company.html', title='Company Management', company=company, stats=stats)

@app.route('/admin/company/edit', methods=['GET', 'POST'])
@admin_required
@company_required
def edit_company():
    """Edit company details"""
    company = g.company

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        max_users = request.form.get('max_users')
        is_active = 'is_active' in request.form

        # Validate input
        error = None
        if not name:
            error = 'Company name is required'
        elif name != company.name and Company.query.filter_by(name=name).first():
            error = 'Company name already exists'

        if max_users:
            try:
                max_users = int(max_users)
                if max_users < 1:
                    error = 'Maximum users must be at least 1'
            except ValueError:
                error = 'Maximum users must be a valid number'
        else:
            max_users = None

        if error is None:
            company.name = name
            company.description = description
            company.max_users = max_users
            company.is_active = is_active
            db.session.commit()

            flash('Company details updated successfully!', 'success')
            return redirect(url_for('admin_company'))
        else:
            flash(error, 'error')

    return render_template('edit_company.html', title='Edit Company', company=company)

@app.route('/admin/company/users')
@admin_required
@company_required
def company_users():
    """List all users in the company with detailed information"""
    users = User.query.filter_by(company_id=g.company.id).order_by(User.created_at.desc()).all()

    # Calculate user statistics
    user_stats = {
        'total': len(users),
        'verified': len([u for u in users if u.is_verified]),
        'unverified': len([u for u in users if not u.is_verified]),
        'blocked': len([u for u in users if u.is_blocked]),
        'active': len([u for u in users if not u.is_blocked and u.is_verified]),
        'admins': len([u for u in users if u.role == Role.ADMIN]),
        'supervisors': len([u for u in users if u.role == Role.SUPERVISOR]),
        'team_leaders': len([u for u in users if u.role == Role.TEAM_LEADER]),
        'team_members': len([u for u in users if u.role == Role.TEAM_MEMBER]),
    }

    return render_template('company_users.html', title='Company Users',
                         users=users, stats=user_stats, company=g.company)

# Add these routes for team management
@app.route('/admin/teams')
@admin_required
@company_required
def admin_teams():
    teams = Team.query.filter_by(company_id=g.user.company_id).all()
    return render_template('admin_teams.html', title='Team Management', teams=teams)

@app.route('/admin/teams/create', methods=['GET', 'POST'])
@admin_required
@company_required
def create_team():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate input
        error = None
        if not name:
            error = 'Team name is required'
        elif Team.query.filter_by(name=name, company_id=g.user.company_id).first():
            error = 'Team name already exists in your company'

        if error is None:
            new_team = Team(name=name, description=description, company_id=g.user.company_id)
            db.session.add(new_team)
            db.session.commit()

            flash(f'Team "{name}" created successfully!', 'success')
            return redirect(url_for('admin_teams'))

        flash(error, 'error')

    return render_template('create_team.html', title='Create Team')

@app.route('/admin/teams/edit/<int:team_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def edit_team(team_id):
    team = Team.query.filter_by(id=team_id, company_id=g.user.company_id).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate input
        error = None
        if not name:
            error = 'Team name is required'
        elif name != team.name and Team.query.filter_by(name=name, company_id=g.user.company_id).first():
            error = 'Team name already exists in your company'

        if error is None:
            team.name = name
            team.description = description
            db.session.commit()

            flash(f'Team "{name}" updated successfully!', 'success')
            return redirect(url_for('admin_teams'))

        flash(error, 'error')

    return render_template('edit_team.html', title='Edit Team', team=team)

@app.route('/admin/teams/delete/<int:team_id>', methods=['POST'])
@admin_required
@company_required
def delete_team(team_id):
    team = Team.query.filter_by(id=team_id, company_id=g.user.company_id).first_or_404()

    # Check if team has members
    if team.users:
        flash('Cannot delete team with members. Remove all members first.', 'error')
        return redirect(url_for('admin_teams'))

    team_name = team.name
    db.session.delete(team)
    db.session.commit()

    flash(f'Team "{team_name}" deleted successfully!', 'success')
    return redirect(url_for('admin_teams'))

@app.route('/admin/teams/<int:team_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def manage_team(team_id):
    team = Team.query.filter_by(id=team_id, company_id=g.user.company_id).first_or_404()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_team':
            # Update team details
            name = request.form.get('name')
            description = request.form.get('description')

            # Validate input
            error = None
            if not name:
                error = 'Team name is required'
            elif name != team.name and Team.query.filter_by(name=name, company_id=g.user.company_id).first():
                error = 'Team name already exists in your company'

            if error is None:
                team.name = name
                team.description = description
                db.session.commit()
                flash(f'Team "{name}" updated successfully!', 'success')
            else:
                flash(error, 'error')

        elif action == 'add_member':
            # Add user to team
            user_id = request.form.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user.team_id = team.id
                    db.session.commit()
                    flash(f'User {user.username} added to team!', 'success')
                else:
                    flash('User not found', 'error')
            else:
                flash('No user selected', 'error')

        elif action == 'remove_member':
            # Remove user from team
            user_id = request.form.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user and user.team_id == team.id:
                    user.team_id = None
                    db.session.commit()
                    flash(f'User {user.username} removed from team!', 'success')
                else:
                    flash('User not found or not in this team', 'error')
            else:
                flash('No user selected', 'error')

    # Get team members
    team_members = User.query.filter_by(team_id=team.id).all()

    # Get users not in this team for the add member form (company-scoped)

    available_users = User.query.filter(
        User.company_id == g.user.company_id,
        (User.team_id != team.id) | (User.team_id == None)
    ).all()

    return render_template(
        'manage_team.html',
        title=f'Manage Team: {team.name}',
        team=team,
        team_members=team_members,
        available_users=available_users
    )

# Project Management Routes
@app.route('/admin/projects')
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage projects
@company_required
def admin_projects():
    projects = Project.query.filter_by(company_id=g.user.company_id).order_by(Project.created_at.desc()).all()
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()
    return render_template('admin_projects.html', title='Project Management', projects=projects, categories=categories)

@app.route('/admin/projects/create', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        code = request.form.get('code')
        team_id = request.form.get('team_id') or None
        category_id = request.form.get('category_id') or None
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Validate input
        error = None
        if not name:
            error = 'Project name is required'
        elif not code:
            error = 'Project code is required'
        elif Project.query.filter_by(code=code, company_id=g.user.company_id).first():
            error = 'Project code already exists in your company'

        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                error = 'Invalid start date format'

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                error = 'Invalid end date format'

        if start_date and end_date and start_date > end_date:
            error = 'Start date cannot be after end date'

        if error is None:
            project = Project(
                name=name,
                description=description,
                code=code.upper(),
                company_id=g.user.company_id,
                team_id=int(team_id) if team_id else None,
                category_id=int(category_id) if category_id else None,
                start_date=start_date,
                end_date=end_date,
                created_by_id=g.user.id
            )
            db.session.add(project)
            db.session.commit()
            flash(f'Project "{name}" created successfully!', 'success')
            return redirect(url_for('admin_projects'))
        else:
            flash(error, 'error')

    # Get available teams and categories for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).order_by(Team.name).all()
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()
    return render_template('create_project.html', title='Create Project', teams=teams, categories=categories)

@app.route('/admin/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def edit_project(project_id):
    project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        code = request.form.get('code')
        team_id = request.form.get('team_id') or None
        category_id = request.form.get('category_id') or None
        is_active = request.form.get('is_active') == 'on'
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Validate input
        error = None
        if not name:
            error = 'Project name is required'
        elif not code:
            error = 'Project code is required'
        elif code != project.code and Project.query.filter_by(code=code, company_id=g.user.company_id).first():
            error = 'Project code already exists in your company'

        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                error = 'Invalid start date format'

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                error = 'Invalid end date format'

        if start_date and end_date and start_date > end_date:
            error = 'Start date cannot be after end date'

        if error is None:
            project.name = name
            project.description = description
            project.code = code.upper()
            project.team_id = int(team_id) if team_id else None
            project.category_id = int(category_id) if category_id else None
            project.is_active = is_active
            project.start_date = start_date
            project.end_date = end_date
            db.session.commit()
            flash(f'Project "{name}" updated successfully!', 'success')
            return redirect(url_for('admin_projects'))
        else:
            flash(error, 'error')

    # Get available teams and categories for the form (company-scoped)
    teams = Team.query.filter_by(company_id=g.user.company_id).order_by(Team.name).all()
    categories = ProjectCategory.query.filter_by(company_id=g.user.company_id).order_by(ProjectCategory.name).all()

    return render_template('edit_project.html', title='Edit Project', project=project, teams=teams, categories=categories)

@app.route('/admin/projects/delete/<int:project_id>', methods=['POST'])
@role_required(Role.ADMIN)  # Only admins can delete projects
@company_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first_or_404()

    # Check if there are time entries associated with this project
    time_entries_count = TimeEntry.query.filter_by(project_id=project_id).count()

    if time_entries_count > 0:
        flash(f'Cannot delete project "{project.name}" - it has {time_entries_count} time entries associated with it. Deactivate the project instead.', 'error')
    else:
        project_name = project.name
        db.session.delete(project)
        db.session.commit()
        flash(f'Project "{project_name}" deleted successfully!', 'success')

    return redirect(url_for('admin_projects'))

@app.route('/api/team/hours_data', methods=['GET'])
@login_required
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can access
@company_required
def team_hours_data():
    # Get the current user's team
    team = Team.query.get(g.user.team_id)

    if not team:
        return jsonify({
            'success': False,
            'message': 'You are not assigned to any team.'
        }), 400

    # Get date range from query parameters or use current week as default
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start_date_str = request.args.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', end_of_week.strftime('%Y-%m-%d'))
    include_self = request.args.get('include_self', 'false') == 'true'

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid date format.'
        }), 400

    # Get all team members
    team_members = User.query.filter_by(team_id=team.id).all()

    # Prepare data structure for team members' hours
    team_data = []

    for member in team_members:
        # Skip if the member is the current user (team leader) and include_self is False
        if member.id == g.user.id and not include_self:
            continue

        # Get time entries for this member in the date range
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == member.id,
            TimeEntry.arrival_time >= datetime.combine(start_date, time.min),
            TimeEntry.arrival_time <= datetime.combine(end_date, time.max)
        ).order_by(TimeEntry.arrival_time).all()

        # Calculate daily and total hours
        daily_hours = {}
        total_seconds = 0

        for entry in entries:
            if entry.duration:  # Only count completed entries
                entry_date = entry.arrival_time.date()
                date_str = entry_date.strftime('%Y-%m-%d')

                if date_str not in daily_hours:
                    daily_hours[date_str] = 0

                daily_hours[date_str] += entry.duration
                total_seconds += entry.duration

        # Convert seconds to hours for display
        for date_str in daily_hours:
            daily_hours[date_str] = round(daily_hours[date_str] / 3600, 2)  # Convert to hours

        total_hours = round(total_seconds / 3600, 2)  # Convert to hours

        # Format entries for JSON response
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                'id': entry.id,
                'arrival_time': entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S'),
                'departure_time': entry.departure_time.strftime('%Y-%m-%d %H:%M:%S') if entry.departure_time else None,
                'duration': entry.duration,
                'total_break_duration': entry.total_break_duration
            })

        # Add member data to team data
        team_data.append({
            'user': {
                'id': member.id,
                'username': member.username,
                'email': member.email
            },
            'daily_hours': daily_hours,
            'total_hours': total_hours,
            'entries': formatted_entries
        })

    # Generate a list of dates in the range for the table header
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    return jsonify({
        'success': True,
        'team': {
            'id': team.id,
            'name': team.name,
            'description': team.description
        },
        'team_data': team_data,
        'date_range': date_range,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })

@app.route('/export')
def export():
    return render_template('export.html', title='Export Data')

def get_date_range(period, start_date_str=None, end_date_str=None):
    """Get start and end date based on period or custom date range."""
    today = datetime.now().date()

    if period:
        if period == 'today':
            return today, today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            return start_date, today
        elif period == 'month':
            start_date = today.replace(day=1)
            return start_date, today
        elif period == 'all':
            earliest_entry = TimeEntry.query.order_by(TimeEntry.arrival_time).first()
            start_date = earliest_entry.arrival_time.date() if earliest_entry else today
            return start_date, today
    else:
        # Custom date range
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            return start_date, end_date
        except (ValueError, TypeError):
            raise ValueError('Invalid date format')

@app.route('/download_export')
def download_export():
    """Handle export download requests."""
    export_format = request.args.get('format', 'csv')
    period = request.args.get('period')

    try:
        start_date, end_date = get_date_range(
            period,
            request.args.get('start_date'),
            request.args.get('end_date')
        )
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD format.')
        return redirect(url_for('export'))

    # Query entries within the date range
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)

    entries = TimeEntry.query.filter(
        TimeEntry.arrival_time >= start_datetime,
        TimeEntry.arrival_time <= end_datetime
    ).order_by(TimeEntry.arrival_time).all()

    if not entries:
        flash('No entries found for the selected date range.')
        return redirect(url_for('export'))

    # Prepare data and filename
    data = prepare_export_data(entries)
    filename = f"timetrack_export_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"

    # Export based on format
    if export_format == 'csv':
        return export_to_csv(data, filename)
    elif export_format == 'excel':
        return export_to_excel(data, filename)
    else:
        flash('Invalid export format.')
        return redirect(url_for('export'))


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
        elif view_type == 'team':
            formatted_data = format_team_data(data, granularity)
        else:
            formatted_data = format_table_data(data)

        return jsonify(formatted_data)

    except Exception as e:
        logger.error(f"Error in analytics_data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def get_filtered_analytics_data(user, mode, start_date=None, end_date=None, project_filter=None):
    """Get filtered time entry data for analytics"""
    # Base query
    query = TimeEntry.query

    # Apply user/team filter
    if mode == 'personal':
        query = query.filter(TimeEntry.user_id == user.id)
    elif mode == 'team' and user.team_id:
        team_user_ids = [u.id for u in User.query.filter_by(team_id=user.team_id).all()]
        query = query.filter(TimeEntry.user_id.in_(team_user_ids))

    # Apply date filters
    if start_date:
        query = query.filter(func.date(TimeEntry.arrival_time) >= start_date)
    if end_date:
        query = query.filter(func.date(TimeEntry.arrival_time) <= end_date)

    # Apply project filter
    if project_filter:
        if project_filter == 'none':
            query = query.filter(TimeEntry.project_id.is_(None))
        else:
            try:
                project_id = int(project_filter)
                query = query.filter(TimeEntry.project_id == project_id)
            except ValueError:
                pass

    return query.order_by(TimeEntry.arrival_time.desc()).all()


@app.route('/api/companies/<int:company_id>/teams')
@system_admin_required
def api_company_teams(company_id):
    """API: Get teams for a specific company (System Admin only)"""
    teams = Team.query.filter_by(company_id=company_id).order_by(Team.name).all()
    return jsonify([{
        'id': team.id,
        'name': team.name,
        'description': team.description
    } for team in teams])

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
@system_admin_required
def api_company_users(company_id):
    """API: Get users for a specific company (System Admin only)"""
    company = Company.query.get_or_404(company_id)
    users = User.query.filter_by(company_id=company.id).order_by(User.username).all()

    return jsonify({
        'company': {
            'id': company.id,
            'name': company.name,
            'is_personal': company.is_personal
        },
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'is_blocked': user.is_blocked,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat(),
            'team_id': user.team_id
        } for user in users]
    })

@app.route('/api/system-admin/users/<int:user_id>/toggle-block', methods=['POST'])
@system_admin_required
def api_toggle_user_block(user_id):
    """API: Toggle user blocked status (System Admin only)"""
    user = User.query.get_or_404(user_id)

    # Safety check: prevent blocking yourself
    if user.id == g.user.id:
        return jsonify({'error': 'Cannot block your own account'}), 400

    # Safety check: prevent blocking the last system admin
    if user.role == Role.SYSTEM_ADMIN and not user.is_blocked:
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN, is_blocked=False).count()
        if system_admin_count <= 1:
            return jsonify({'error': 'Cannot block the last system administrator'}), 400

    user.is_blocked = not user.is_blocked
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_blocked': user.is_blocked,
        'message': f'User {"blocked" if user.is_blocked else "unblocked"} successfully'
    })

@app.route('/api/system-admin/companies/<int:company_id>/stats')
@system_admin_required
def api_company_stats(company_id):
    """API: Get detailed statistics for a specific company"""
    company = Company.query.get_or_404(company_id)

    # User counts by role
    role_counts = {}
    for role in Role:
        count = User.query.filter_by(company_id=company.id, role=role).count()
        if count > 0:
            role_counts[role.value] = count

    # Team and project counts
    team_count = Team.query.filter_by(company_id=company.id).count()
    project_count = Project.query.filter_by(company_id=company.id).count()
    active_projects = Project.query.filter_by(company_id=company.id, is_active=True).count()

    # Time entries statistics
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    month_ago = datetime.now() - timedelta(days=30)

    weekly_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= week_ago
    ).count()

    monthly_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= month_ago
    ).count()

    # Active sessions
    active_sessions = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.departure_time == None,
        TimeEntry.is_paused == False
    ).count()

    return jsonify({
        'company': {
            'id': company.id,
            'name': company.name,
            'is_personal': company.is_personal,
            'is_active': company.is_active
        },
        'users': {
            'total': sum(role_counts.values()),
            'by_role': role_counts
        },
        'structure': {
            'teams': team_count,
            'projects': project_count,
            'active_projects': active_projects
        },
        'activity': {
            'weekly_entries': weekly_entries,
            'monthly_entries': monthly_entries,
            'active_sessions': active_sessions
        }
    })

@app.route('/api/analytics/export')
@login_required
def analytics_export():
    """Export analytics data in various formats"""
    export_format = request.args.get('format', 'csv')
    view_type = request.args.get('view', 'table')
    mode = request.args.get('mode', 'personal')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    project_filter = request.args.get('project_id')

    # Validate permissions
    if mode == 'team':
        if not g.user.team_id:
            flash('No team assigned', 'error')
            return redirect(url_for('analytics'))
        if g.user.role not in [Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]:
            flash('Insufficient permissions', 'error')
            return redirect(url_for('analytics'))

    try:
        # Parse dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get data
        data = get_filtered_analytics_data(g.user, mode, start_date, end_date, project_filter)

        if export_format == 'csv':
            return export_analytics_csv(data, view_type, mode)
        elif export_format == 'excel':
            return export_analytics_excel(data, view_type, mode)
        else:
            flash('Invalid export format', 'error')
            return redirect(url_for('analytics'))

    except Exception as e:
        logger.error(f"Error in analytics export: {str(e)}")
        flash('Error generating export', 'error')
        return redirect(url_for('analytics'))

# Task Management Routes
@app.route('/admin/projects/<int:project_id>/tasks')
@role_required(Role.TEAM_MEMBER)  # All authenticated users can view tasks
@company_required
def manage_project_tasks(project_id):
    project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first_or_404()

    # Check if user has access to this project
    if not project.is_user_allowed(g.user):
        flash('You do not have access to this project.', 'error')
        return redirect(url_for('admin_projects'))

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

# Task API Routes
@app.route('/api/tasks', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def create_task():
    try:
        data = request.get_json()
        project_id = data.get('project_id')

        # Verify project access
        project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first()
        if not project or not project.is_user_allowed(g.user):
            return jsonify({'success': False, 'message': 'Project not found or access denied'})

        # Validate required fields
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Task name is required'})

        # Parse dates
        start_date = None
        due_date = None
        if data.get('start_date'):
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        if data.get('due_date'):
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()

        # Create task
        task = Task(
            name=name,
            description=data.get('description', ''),
            status=TaskStatus(data.get('status', 'Not Started')),
            priority=TaskPriority(data.get('priority', 'Medium')),
            estimated_hours=float(data.get('estimated_hours')) if data.get('estimated_hours') else None,
            project_id=project_id,
            assigned_to_id=int(data.get('assigned_to_id')) if data.get('assigned_to_id') else None,
            start_date=start_date,
            due_date=due_date,
            created_by_id=g.user.id
        )

        db.session.add(task)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Task created successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@role_required(Role.TEAM_MEMBER)
@company_required
def get_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        task_data = {
            'id': task.id,
            'name': task.name,
            'description': task.description,
            'status': task.status.value,
            'priority': task.priority.value,
            'estimated_hours': task.estimated_hours,
            'assigned_to_id': task.assigned_to_id,
            'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else None,
            'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None
        }

        return jsonify({'success': True, 'task': task_data})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        data = request.get_json()

        # Update task fields
        if 'name' in data:
            task.name = data['name']
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            task.status = TaskStatus(data['status'])
            if data['status'] == 'Completed':
                task.completed_date = datetime.now().date()
            else:
                task.completed_date = None
        if 'priority' in data:
            task.priority = TaskPriority(data['priority'])
        if 'estimated_hours' in data:
            task.estimated_hours = float(data['estimated_hours']) if data['estimated_hours'] else None
        if 'assigned_to_id' in data:
            task.assigned_to_id = int(data['assigned_to_id']) if data['assigned_to_id'] else None
        if 'start_date' in data:
            task.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'due_date' in data:
            task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None

        db.session.commit()

        return jsonify({'success': True, 'message': 'Task updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can delete tasks
@company_required
def delete_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        db.session.delete(task)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Task deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Subtask API Routes
@app.route('/api/subtasks', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def create_subtask():
    try:
        data = request.get_json()
        task_id = data.get('task_id')

        # Verify task access
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        # Validate required fields
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Subtask name is required'})

        # Parse dates
        start_date = None
        due_date = None
        if data.get('start_date'):
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        if data.get('due_date'):
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()

        # Create subtask
        subtask = SubTask(
            name=name,
            description=data.get('description', ''),
            status=TaskStatus(data.get('status', 'Not Started')),
            priority=TaskPriority(data.get('priority', 'Medium')),
            estimated_hours=float(data.get('estimated_hours')) if data.get('estimated_hours') else None,
            task_id=task_id,
            assigned_to_id=int(data.get('assigned_to_id')) if data.get('assigned_to_id') else None,
            start_date=start_date,
            due_date=due_date,
            created_by_id=g.user.id
        )

        db.session.add(subtask)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask created successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/subtasks/<int:subtask_id>', methods=['GET'])
@role_required(Role.TEAM_MEMBER)
@company_required
def get_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        subtask_data = {
            'id': subtask.id,
            'name': subtask.name,
            'description': subtask.description,
            'status': subtask.status.value,
            'priority': subtask.priority.value,
            'estimated_hours': subtask.estimated_hours,
            'assigned_to_id': subtask.assigned_to_id,
            'start_date': subtask.start_date.strftime('%Y-%m-%d') if subtask.start_date else None,
            'due_date': subtask.due_date.strftime('%Y-%m-%d') if subtask.due_date else None
        }

        return jsonify({'success': True, 'subtask': subtask_data})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/subtasks/<int:subtask_id>', methods=['PUT'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        data = request.get_json()

        # Update subtask fields
        if 'name' in data:
            subtask.name = data['name']
        if 'description' in data:
            subtask.description = data['description']
        if 'status' in data:
            subtask.status = TaskStatus(data['status'])
            if data['status'] == 'Completed':
                subtask.completed_date = datetime.now().date()
            else:
                subtask.completed_date = None
        if 'priority' in data:
            subtask.priority = TaskPriority(data['priority'])
        if 'estimated_hours' in data:
            subtask.estimated_hours = float(data['estimated_hours']) if data['estimated_hours'] else None
        if 'assigned_to_id' in data:
            subtask.assigned_to_id = int(data['assigned_to_id']) if data['assigned_to_id'] else None
        if 'start_date' in data:
            subtask.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'due_date' in data:
            subtask.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None

        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/subtasks/<int:subtask_id>', methods=['DELETE'])
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can delete subtasks
@company_required
def delete_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        db.session.delete(subtask)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Category Management API Routes
@app.route('/api/admin/categories', methods=['POST'])
@role_required(Role.ADMIN)
@company_required
def create_category():
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        color = data.get('color', '#007bff')
        icon = data.get('icon', '')

        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'})

        # Check if category already exists
        existing = ProjectCategory.query.filter_by(
            name=name,
            company_id=g.user.company_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Category name already exists'})

        category = ProjectCategory(
            name=name,
            description=description,
            color=color,
            icon=icon,
            company_id=g.user.company_id,
            created_by_id=g.user.id
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category created successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/categories/<int:category_id>', methods=['PUT'])
@role_required(Role.ADMIN)
@company_required
def update_category(category_id):
    try:
        category = ProjectCategory.query.filter_by(
            id=category_id,
            company_id=g.user.company_id
        ).first()

        if not category:
            return jsonify({'success': False, 'message': 'Category not found'})

        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'})

        # Check if name conflicts with another category
        existing = ProjectCategory.query.filter(
            ProjectCategory.name == name,
            ProjectCategory.company_id == g.user.company_id,
            ProjectCategory.id != category_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Category name already exists'})

        category.name = name
        category.description = data.get('description', '')
        category.color = data.get('color', category.color)
        category.icon = data.get('icon', '')

        db.session.commit()

        return jsonify({'success': True, 'message': 'Category updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/categories/<int:category_id>', methods=['DELETE'])
@role_required(Role.ADMIN)
@company_required
def delete_category(category_id):
    try:
        category = ProjectCategory.query.filter_by(
            id=category_id,
            company_id=g.user.company_id
        ).first()

        if not category:
            return jsonify({'success': False, 'message': 'Category not found'})

        # Unassign projects from this category
        projects = Project.query.filter_by(category_id=category_id).all()
        for project in projects:
            project.category_id = None

        db.session.delete(category)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)