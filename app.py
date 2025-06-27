from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from models import db, TimeEntry, WorkConfig
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_timetrack')  # Add secret key for flash messages

# Initialize the database with the app
db.init_app(app)

@app.route('/')
def home():
    # Get the latest time entry that doesn't have a departure time
    active_entry = TimeEntry.query.filter_by(departure_time=None).first()

    # Get all completed time entries, ordered by most recent first
    history = TimeEntry.query.filter(TimeEntry.departure_time.isnot(None)).order_by(TimeEntry.arrival_time.desc()).all()

    return render_template('index.html', title='Home', active_entry=active_entry, history=history)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    # redacted
    return render_template('contact.html', title='Contact')

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html', title='Thank You')

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

    # Calculate duration in seconds (excluding breaks)
    raw_duration = (departure_time - entry.arrival_time).total_seconds()
    entry.duration = int(raw_duration - entry.total_break_duration)

    db.session.commit()

    return jsonify({
        'id': entry.id,
        'arrival_time': entry.arrival_time.strftime('%Y-%m-%d %H:%M:%S'),
        'departure_time': entry.departure_time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': entry.duration,
        'total_break_duration': entry.total_break_duration
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

if __name__ == '__main__':
    app.run(debug=True)