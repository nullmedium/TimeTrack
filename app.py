from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from models import db, TimeEntry, WorkConfig
from datetime import datetime, time
import os
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_timetrack')  # Add secret key for flash messages

# Initialize the database with the app
db.init_app(app)

@app.route('/')
def home():
    # Get active time entry (if any)
    active_entry = TimeEntry.query.filter_by(departure_time=None).first()

    # Get today's date
    today = datetime.now().date()

    # Get time entries for today only
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)

    today_entries = TimeEntry.query.filter(
        TimeEntry.arrival_time >= today_start,
        TimeEntry.arrival_time <= today_end
    ).order_by(TimeEntry.arrival_time.desc()).all()

    return render_template('index.html', title='Home', active_entry=active_entry, history=today_entries)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    # redacted
    return render_template('contact.html', title='Contact')

# We can keep this route as a redirect to home for backward compatibility
@app.route('/timetrack')
def timetrack():
    return redirect(url_for('home'))

@app.route('/api/arrive', methods=['POST'])
def arrive():
    # Create a new time entry with arrival time
    new_entry = TimeEntry(arrival_time=datetime.now())
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({
        'id': new_entry.id,
        'arrival_time': new_entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/leave/<int:entry_id>', methods=['POST'])
def leave(entry_id):
    # Find the time entry
    entry = TimeEntry.query.get_or_404(entry_id)

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
def toggle_pause(entry_id):
    # Find the time entry
    entry = TimeEntry.query.get_or_404(entry_id)

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
def delete_entry(entry_id):
    entry = TimeEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Entry deleted successfully'})

@app.route('/api/update/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    entry = TimeEntry.query.get_or_404(entry_id)
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
def history():
    # Get all time entries, ordered by most recent first
    all_entries = TimeEntry.query.order_by(TimeEntry.arrival_time.desc()).all()

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

    # Calculate mandatory breaks based on work duration
    work_hours = raw_duration / 3600  # Convert seconds to hours
    configured_break_seconds = 0

    # Apply primary break if work duration exceeds threshold
    if work_hours > config.break_threshold_hours:
        configured_break_seconds += config.mandatory_break_minutes * 60

    # Apply additional break if work duration exceeds additional threshold
    if work_hours > config.additional_break_threshold_hours:
        configured_break_seconds += config.additional_break_minutes * 60

    # Use the greater of configured breaks or actual logged breaks
    effective_break_duration = max(configured_break_seconds, total_break_duration)

    # Calculate final work duration
    work_duration = int(raw_duration - effective_break_duration)

    return work_duration, effective_break_duration

@app.route('/api/resume/<int:entry_id>', methods=['POST'])
def resume_entry(entry_id):
    # Find the entry to resume
    entry_to_resume = TimeEntry.query.get_or_404(entry_id)

    # Check if there's already an active entry
    active_entry = TimeEntry.query.filter_by(departure_time=None).first()
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

if __name__ == '__main__':
    app.run(debug=True)