from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, g
from models import db, TimeEntry, WorkConfig, User, SystemSettings, Team, Role
import logging
from datetime import datetime, time, timedelta
import os
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetrack.db'
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

# Add this function to initialize system settings
def init_system_settings():
    # Check if registration_enabled setting exists, if not create it
    if not SystemSettings.query.filter_by(key='registration_enabled').first():
        registration_setting = SystemSettings(
            key='registration_enabled',
            value='true',
            description='Controls whether new user registration is allowed'
        )
        db.session.add(registration_setting)
        db.session.commit()

# Call this function during app initialization (add it where you initialize the app)
@app.before_first_request
def initialize_app():
    init_system_settings()

# Add this after initializing the app but before defining routes
@app.context_processor
def inject_globals():
    """Make certain variables available to all templates."""
    return {
        'Role': Role,
        'current_year': datetime.now().year
    }

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
        if g.user is None or not g.user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

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
            
            # Admin always has access
            if g.user.is_admin:
                return f(*args, **kwargs)
            
            # Check role hierarchy
            role_hierarchy = {
                Role.TEAM_MEMBER: 1,
                Role.TEAM_LEADER: 2,
                Role.SUPERVISOR: 3,
                Role.ADMIN: 4
            }
            
            if role_hierarchy.get(g.user.role, 0) < role_hierarchy.get(min_role, 0):
                flash('You do not have sufficient permissions to access this page.', 'error')
                return redirect(url_for('home'))
                
            return f(*args, **kwargs)
        return decorated_function
    return role_decorator

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)
        if g.user and not g.user.is_verified and request.endpoint not in ['verify_email', 'static', 'logout']:
            # Allow unverified users to access only verification and static resources
            if request.endpoint not in ['login', 'register']:
                flash('Please verify your email address before accessing this page.', 'warning')
                session.clear()
                return redirect(url_for('login'))

@app.route('/')
def home():
    if g.user:
        # Get active entry (no departure time)
        active_entry = TimeEntry.query.filter_by(
            user_id=g.user.id, 
            departure_time=None
        ).first()
        
        # Get recent completed entries for history (last 10 entries)
        history = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            TimeEntry.departure_time.isnot(None)
        ).order_by(TimeEntry.arrival_time.desc()).limit(10).all()
        
        return render_template('index.html', title='Home', active_entry=active_entry, history=history)
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
                    user.role = Role.ADMIN if user.is_admin else Role.TEAM_MEMBER
                
                db.session.commit()
            
            # Now proceed with password check
            if user.check_password(password):
                # Check if user is blocked
                if user.is_blocked:
                    flash('Your account has been disabled. Please contact an administrator.', 'error')
                    return render_template('login.html')
                    
                # Continue with normal login process
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                
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
    reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
    registration_enabled = reg_setting and reg_setting.value == 'true'
    
    if not registration_enabled:
        flash('Registration is currently disabled by the administrator.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
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
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists'
        elif User.query.filter_by(email=email).first():
            error = 'Email already registered'
            
        if error is None:
            try:
                new_user = User(username=username, email=email, is_verified=False)
                new_user.set_password(password)
                
                # Generate verification token
                token = new_user.generate_verification_token()
                
                db.session.add(new_user)
                db.session.commit()
                
                # Send verification email
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
    
    if g.user.is_admin or g.user.role == Role.ADMIN:
        # Admin sees everything
        dashboard_data.update({
            'total_users': User.query.count(),
            'total_teams': Team.query.count(),
            'blocked_users': User.query.filter_by(is_blocked=True).count(),
            'unverified_users': User.query.filter_by(is_verified=False).count(),
            'recent_registrations': User.query.order_by(User.id.desc()).limit(5).all()
        })
    
    if g.user.role in [Role.TEAM_LEADER, Role.SUPERVISOR] or g.user.is_admin:
        # Team leaders and supervisors see team-related data
        if g.user.team_id or g.user.is_admin:
            if g.user.is_admin:
                # Admin can see all teams
                teams = Team.query.all()
                team_members = User.query.filter(User.team_id.isnot(None)).all()
            else:
                # Team leaders/supervisors see their own team
                teams = [Team.query.get(g.user.team_id)] if g.user.team_id else []
                team_members = User.query.filter_by(team_id=g.user.team_id).all() if g.user.team_id else []
            
            dashboard_data.update({
                'teams': teams,
                'team_members': team_members,
                'team_member_count': len(team_members)
            })
    
    # Get recent time entries for the user's oversight
    if g.user.is_admin:
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
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return redirect(url_for('dashboard'))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', title='User Management', users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
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
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists'
        elif User.query.filter_by(email=email).first():
            error = 'Email already registered'
            
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
                is_admin=is_admin, 
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
    
    # Get all teams for the form
    teams = Team.query.all()
    roles = [role for role in Role]
    
    return render_template('create_user.html', title='Create User', teams=teams, roles=roles)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        
        # Get role and team
        role_name = request.form.get('role')
        team_id = request.form.get('team_id')
        
        # Validate input
        error = None
        if not username:
            error = 'Username is required'
        elif not email:
            error = 'Email is required'
        elif username != user.username and User.query.filter_by(username=username).first():
            error = 'Username already exists'
        elif email != user.email and User.query.filter_by(email=email).first():
            error = 'Email already registered'
            
        if error is None:
            user.username = username
            user.email = email
            user.is_admin = is_admin
            
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
    
    # Get all teams for the form
    teams = Team.query.all()
    roles = [role for role in Role]
    
    return render_template('edit_user.html', title='Edit User', user=user, teams=teams, roles=roles)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
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

@app.route('/about')
@login_required
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
    # Create a new time entry with arrival time for the current user
    new_entry = TimeEntry(user_id=session['user_id'], arrival_time=datetime.now())
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({
        'id': new_entry.id,
        'arrival_time': new_entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/leave/<int:entry_id>', methods=['POST'])
@login_required
def leave(entry_id):
    # Find the time entry for the current user
    entry = TimeEntry.query.filter_by(id=entry_id, user_id=session['user_id']).first_or_404()

    # Set the departure time
    departure_time = datetime.now()
    entry.departure_time = departure_time

    # If currently paused, add the final break duration
    if entry.is_paused and entry.pause_start_time:
        final_break_duration = int((departure_time - entry.pause_start_time).total_seconds())
        entry.total_break_duration += final_break_duration
        entry.is_paused = False
        entry.pause_start_time = None

    # Calculate work duration considering breaks
    entry.duration, effective_break = calculate_work_duration(
        entry.arrival_time,
        departure_time,
        entry.total_break_duration
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
    # Get current configuration or create default if none exists
    config = WorkConfig.query.order_by(WorkConfig.id.desc()).first()
    if not config:
        config = WorkConfig()
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        try:
            # Update configuration with form data
            config.work_hours_per_day = float(request.form.get('work_hours_per_day', 8.0))
            config.mandatory_break_minutes = int(request.form.get('mandatory_break_minutes', 30))
            config.break_threshold_hours = float(request.form.get('break_threshold_hours', 6.0))
            config.additional_break_minutes = int(request.form.get('additional_break_minutes', 15))
            config.additional_break_threshold_hours = float(request.form.get('additional_break_threshold_hours', 9.0))

            db.session.commit()
            flash('Configuration updated successfully!', 'success')
            return redirect(url_for('config'))
        except ValueError:
            flash('Please enter valid numbers for all fields', 'error')

    return render_template('config.html', title='Configuration', config=config)

# Create the database tables before first request
@app.before_first_request
def create_tables():
    # This will only create tables that don't exist yet
    db.create_all()

    # Check if we need to add new columns
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    # Check if user table exists
    if 'user' in inspector.get_table_names():
        columns = [column['name'] for column in inspector.get_columns('user')]
        
        # Check for verification columns
        if 'is_verified' not in columns or 'verification_token' not in columns or 'token_expiry' not in columns:
            logger.warning("Database schema is outdated. Please run migrate_db.py to update it.")
            print("WARNING: Database schema is outdated. Please run migrate_db.py to update it.")

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
                    entry.total_break_duration
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

@app.route('/team/hours')
@login_required
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can access
def team_hours():
    # Get the current user's team
    team = Team.query.get(g.user.team_id)
    
    if not team:
        flash('You are not assigned to any team.', 'error')
        return redirect(url_for('home'))
    
    # Get date range from query parameters or use current week as default
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_date_str = request.args.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', end_of_week.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format. Using current week instead.', 'warning')
        start_date = start_of_week
        end_date = end_of_week
    
    # Generate a list of dates in the range for the table header
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    return render_template(
        'team_hours.html',
        title=f'Team Hours',
        start_date=start_date,
        end_date=end_date,
        date_range=date_range
    )

@app.route('/history')
@login_required
def history():
    # Get all time entries for the current user, ordered by most recent first
    all_entries = TimeEntry.query.filter_by(user_id=session['user_id']).order_by(TimeEntry.arrival_time.desc()).all()

    return render_template('history.html', title='Time Entry History', entries=all_entries)

def calculate_work_duration(arrival_time, departure_time, total_break_duration):
    """
    Calculate work duration considering both configured and actual break times.

    Args:
        arrival_time: Datetime of arrival
        departure_time: Datetime of departure
        total_break_duration: Actual logged break duration in seconds

    Returns:
        tuple: (work_duration_in_seconds, effective_break_duration_in_seconds)
    """
    # Calculate raw duration
    raw_duration = (departure_time - arrival_time).total_seconds()

    # Get work configuration for break rules
    config = WorkConfig.query.order_by(WorkConfig.id.desc()).first()
    if not config:
        config = WorkConfig()  # Use default values if no config exists

    # Ensure configuration values are not None, use defaults if they are
    break_threshold_hours = config.break_threshold_hours if config.break_threshold_hours is not None else 6.0
    mandatory_break_minutes = config.mandatory_break_minutes if config.mandatory_break_minutes is not None else 30
    additional_break_threshold_hours = config.additional_break_threshold_hours if config.additional_break_threshold_hours is not None else 9.0
    additional_break_minutes = config.additional_break_minutes if config.additional_break_minutes is not None else 15

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
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
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
            db.session.commit()
            flash('System settings updated successfully!', 'success')
        
    # Get current settings
    settings = {}
    for setting in SystemSettings.query.all():
        if setting.key == 'registration_enabled':
            settings['registration_enabled'] = setting.value == 'true'
    
    return render_template('admin_settings.html', title='System Settings', settings=settings)

# Add these routes for team management
@app.route('/admin/teams')
@admin_required
def admin_teams():
    teams = Team.query.all()
    return render_template('admin_teams.html', title='Team Management', teams=teams)

@app.route('/admin/teams/create', methods=['GET', 'POST'])
@admin_required
def create_team():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Validate input
        error = None
        if not name:
            error = 'Team name is required'
        elif Team.query.filter_by(name=name).first():
            error = 'Team name already exists'
            
        if error is None:
            new_team = Team(name=name, description=description)
            db.session.add(new_team)
            db.session.commit()
            
            flash(f'Team "{name}" created successfully!', 'success')
            return redirect(url_for('admin_teams'))
        
        flash(error, 'error')
    
    return render_template('create_team.html', title='Create Team')

@app.route('/admin/teams/edit/<int:team_id>', methods=['GET', 'POST'])
@admin_required
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Validate input
        error = None
        if not name:
            error = 'Team name is required'
        elif name != team.name and Team.query.filter_by(name=name).first():
            error = 'Team name already exists'
            
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
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    
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
def manage_team(team_id):
    team = Team.query.get_or_404(team_id)
    
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
            elif name != team.name and Team.query.filter_by(name=name).first():
                error = 'Team name already exists'
                
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
    
    # Get users not in this team for the add member form
    available_users = User.query.filter(
        (User.team_id != team.id) | (User.team_id == None)
    ).all()
    
    return render_template(
        'manage_team.html', 
        title=f'Manage Team: {team.name}', 
        team=team, 
        team_members=team_members,
        available_users=available_users
    )

@app.route('/api/team/hours_data', methods=['GET'])
@login_required
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can access
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

if __name__ == '__main__':
    app.run(debug=True)