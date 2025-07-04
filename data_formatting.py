"""
Data formatting utilities for TimeTrack application.
Handles conversion of time entries and analytics data to various display formats.
"""

from datetime import datetime
from collections import defaultdict


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS format."""
    if seconds is None:
        return '00:00:00'
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:d}:{minutes:02d}:{seconds:02d}"


def prepare_export_data(entries):
    """Prepare time entries data for export."""
    data = []
    for entry in entries:
        row = {
            'Date': entry.arrival_time.strftime('%Y-%m-%d'),
            'Project Code': entry.project.code if entry.project else '',
            'Project Name': entry.project.name if entry.project else '',
            'Arrival Time': entry.arrival_time.strftime('%H:%M:%S'),
            'Departure Time': entry.departure_time.strftime('%H:%M:%S') if entry.departure_time else 'Active',
            'Work Duration (HH:MM:SS)': format_duration(entry.duration) if entry.duration is not None else 'In progress',
            'Break Duration (HH:MM:SS)': format_duration(entry.total_break_duration),
            'Work Duration (seconds)': entry.duration if entry.duration is not None else 0,
            'Break Duration (seconds)': entry.total_break_duration if entry.total_break_duration is not None else 0,
            'Notes': entry.notes if entry.notes else ''
        }
        data.append(row)
    return data


def prepare_team_hours_export_data(team, team_data, date_range):
    """Prepare team hours data for export."""
    export_data = []
    
    for member_data in team_data:
        user = member_data['user']
        daily_hours = member_data['daily_hours']
        
        # Create base row with member info
        row = {
            'Team': team['name'],
            'Member': user['username'],
            'Email': user['email'],
            'Total Hours': member_data['total_hours']
        }
        
        # Add daily hours columns
        for date_str in date_range:
            formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d/%Y')
            row[formatted_date] = daily_hours.get(date_str, 0.0)
        
        export_data.append(row)
    
    return export_data


def format_table_data(entries):
    """Format data for table view in analytics."""
    formatted_entries = []
    for entry in entries:
        formatted_entry = {
            'id': entry.id,
            'date': entry.arrival_time.strftime('%Y-%m-%d'),
            'arrival_time': entry.arrival_time.strftime('%H:%M:%S'),
            'departure_time': entry.departure_time.strftime('%H:%M:%S') if entry.departure_time else 'Active',
            'duration': format_duration(entry.duration) if entry.duration else 'In progress',
            'break_duration': format_duration(entry.total_break_duration),
            'project_code': entry.project.code if entry.project else None,
            'project_name': entry.project.name if entry.project else 'No Project',
            'notes': entry.notes or '',
            'user_name': entry.user.username
        }
        formatted_entries.append(formatted_entry)
    
    return {'entries': formatted_entries}


def format_graph_data(entries, granularity='daily'):
    """Format data for graph visualization in analytics."""
    # Group data by date
    daily_data = defaultdict(lambda: {'total_hours': 0, 'projects': defaultdict(int)})
    project_totals = defaultdict(int)
    
    for entry in entries:
        if entry.departure_time and entry.duration:
            date_key = entry.arrival_time.strftime('%Y-%m-%d')
            hours = entry.duration / 3600  # Convert seconds to hours
            
            daily_data[date_key]['total_hours'] += hours
            project_name = entry.project.name if entry.project else 'No Project'
            daily_data[date_key]['projects'][project_name] += hours
            project_totals[project_name] += hours
    
    # Format time series data
    time_series = []
    for date, data in sorted(daily_data.items()):
        time_series.append({
            'date': date,
            'hours': round(data['total_hours'], 2)
        })
    
    # Format project distribution
    project_distribution = [
        {'project': project, 'hours': round(hours, 2)}
        for project, hours in project_totals.items()
    ]
    
    return {
        'timeSeries': time_series,
        'projectDistribution': project_distribution,
        'totalHours': sum(project_totals.values()),
        'totalDays': len(daily_data)
    }


def format_team_data(entries, granularity='daily'):
    """Format data for team view in analytics."""
    # Group by user and date
    user_data = defaultdict(lambda: {'daily_hours': defaultdict(float), 'total_hours': 0})
    
    for entry in entries:
        if entry.departure_time and entry.duration:
            date_key = entry.arrival_time.strftime('%Y-%m-%d')
            hours = entry.duration / 3600
            
            user_data[entry.user.username]['daily_hours'][date_key] += hours
            user_data[entry.user.username]['total_hours'] += hours
    
    # Format for frontend
    team_data = []
    for username, data in user_data.items():
        team_data.append({
            'username': username,
            'daily_hours': dict(data['daily_hours']),
            'total_hours': round(data['total_hours'], 2)
        })
    
    return {'team_data': team_data}


def format_burndown_data(tasks, start_date, end_date):
    """Format data for burndown chart visualization."""
    from datetime import datetime, timedelta
    from models import Task, TaskStatus
    
    if not tasks:
        return {'burndown': {'dates': [], 'remaining': [], 'ideal': []}}
    
    # Convert string dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate date range
    current_date = start_date
    dates = []
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    total_tasks = len(tasks)
    if total_tasks == 0:
        return {'burndown': {'dates': dates, 'remaining': [0] * len(dates), 'ideal': [0] * len(dates)}}
    
    # Calculate ideal burndown (linear decrease from total to 0)
    total_days = len(dates)
    ideal_burndown = []
    for i in range(total_days):
        remaining_ideal = total_tasks - (total_tasks * i / (total_days - 1)) if total_days > 1 else 0
        ideal_burndown.append(max(0, round(remaining_ideal, 1)))
    
    # Calculate actual remaining tasks for each date
    actual_remaining = []
    for date_str in dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Count tasks not completed by this date
        remaining_count = 0
        for task in tasks:
            # Task is remaining if:
            # 1. It's not completed, OR
            # 2. It was completed after this date
            if task.status != TaskStatus.COMPLETED:
                remaining_count += 1
            elif task.completed_date and task.completed_date > date_obj:
                remaining_count += 1
        
        actual_remaining.append(remaining_count)
    
    return {
        'burndown': {
            'dates': dates,
            'remaining': actual_remaining,
            'ideal': ideal_burndown,
            'total_tasks': total_tasks,
            'tasks_completed': total_tasks - (actual_remaining[-1] if actual_remaining else total_tasks)
        }
    }