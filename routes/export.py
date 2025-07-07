"""
Export routes for TimeTrack application.
Handles data export functionality for time entries and analytics.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from datetime import datetime, time, timedelta
from models import db, TimeEntry, Role, Project
from data_formatting import prepare_export_data
from data_export import export_to_csv, export_to_excel
from routes.auth import login_required, company_required

# Create blueprint
export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/')
@login_required
@company_required
def export_page():
    """Display the export page."""
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


@export_bp.route('/download')
@login_required
@company_required
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
        return redirect(url_for('export.export_page'))

    # Query entries within the date range
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)

    entries = TimeEntry.query.filter(
        TimeEntry.arrival_time >= start_datetime,
        TimeEntry.arrival_time <= end_datetime
    ).order_by(TimeEntry.arrival_time).all()

    if not entries:
        flash('No entries found for the selected date range.')
        return redirect(url_for('export.export_page'))

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
        return redirect(url_for('export.export_page'))