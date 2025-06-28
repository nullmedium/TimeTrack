from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, g
from models import db, TimeEntry, WorkConfig, User
import logging
from datetime import datetime, time, timedelta
import os
from sqlalchemy import func
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_timetrack')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts for 7 days

# Initialize the database with the app
db.init_app(app)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Admin-only decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('You need administrator privileges to access this page', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

@app.route('/')
def home():
    if g.user:
        # Get active time entry (if any) for the current user
        active_entry = TimeEntry.query.filter_by(user_id=g.user.id, departure_time=None).first()

        # Get today's date
        today = datetime.now().date()

        # Get time entries for today only for the current user
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)

        today_entries = TimeEntry.query.filter(
            TimeEntry.user_id == g.user.id,
            TimeEntry.arrival_time >= today_start,
            TimeEntry.arrival_time <= today_end
        ).order_by(TimeEntry.arrival_time.desc()).all()

        return render_template('index.html', title='Home', active_entry=active_entry, history=today_entries)
    else:
        # Show landing page for non-logged in users
        return render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            if remember:
                session.permanent = True
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('home')
                
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
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
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        
        flash(error, 'error')
    
    return render_template('register.html', title='Register')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', title='Admin Dashboard')

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
            new_user = User(username=username, email=email, is_admin=is_admin)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        flash(error, 'error')
    
    return render_template('create_user.html', title='Create User')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        
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
            
            if password:
                user.set_password(password)
            
            db.session.commit()
            
            flash(f'User {username} updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        flash(error, 'error')
    
    return render_template('edit_user.html', title='Edit User', user=user)

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
    columns = [column['name'] for column in inspector.get_columns('time_entry')]

    if 'is_paused' not in columns or 'pause_start_time' not in columns or 'total_break_duration' not in columns:
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

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

if __name__ == '__main__':
    app.run(debug=True)