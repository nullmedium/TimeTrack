"""
Time utility functions for TimeTrack application.
Includes time rounding functionality.
"""

from datetime import datetime, timedelta
import math


def round_time_to_interval(dt, interval_minutes, round_to_nearest=True):
    """
    Round a datetime to the specified interval.
    
    Args:
        dt (datetime): The datetime to round
        interval_minutes (int): The interval in minutes (15, 30, etc.)
        round_to_nearest (bool): If True, round to nearest interval; if False, round up
        
    Returns:
        datetime: The rounded datetime
    """
    if interval_minutes == 0:
        return dt  # No rounding
    
    # Calculate the number of minutes from midnight
    minutes_from_midnight = dt.hour * 60 + dt.minute
    
    if round_to_nearest:
        # Round to nearest interval
        rounded_minutes = round(minutes_from_midnight / interval_minutes) * interval_minutes
    else:
        # Round up to next interval
        rounded_minutes = math.ceil(minutes_from_midnight / interval_minutes) * interval_minutes
    
    # Convert back to hours and minutes
    rounded_hour = int(rounded_minutes // 60)
    rounded_minute = int(rounded_minutes % 60)
    
    # Handle case where rounding goes to next day
    if rounded_hour >= 24:
        rounded_hour = 0
        dt = dt + timedelta(days=1)
    
    # Create new datetime with rounded time (keep seconds as 0)
    return dt.replace(hour=rounded_hour, minute=rounded_minute, second=0, microsecond=0)


def round_duration_to_interval(duration_seconds, interval_minutes, round_to_nearest=True):
    """
    Round a duration to the specified interval.
    
    Args:
        duration_seconds (int): The duration in seconds
        interval_minutes (int): The interval in minutes (15, 30, etc.)
        round_to_nearest (bool): If True, round to nearest interval; if False, round up
        
    Returns:
        int: The rounded duration in seconds
    """
    if interval_minutes == 0:
        return duration_seconds  # No rounding
    
    # Convert to minutes
    duration_minutes = duration_seconds / 60
    interval_seconds = interval_minutes * 60
    
    if round_to_nearest:
        # Round to nearest interval
        rounded_intervals = round(duration_minutes / interval_minutes)
    else:
        # Round up to next interval
        rounded_intervals = math.ceil(duration_minutes / interval_minutes)
    
    return int(rounded_intervals * interval_seconds)


def get_user_rounding_settings(user):
    """
    Get the time rounding settings for a user.
    
    Args:
        user: The user object
        
    Returns:
        tuple: (interval_minutes, round_to_nearest)
    """
    work_config = user.work_config
    if work_config:
        return work_config.time_rounding_minutes, work_config.round_to_nearest
    else:
        return 0, True  # Default: no rounding, round to nearest


def apply_time_rounding(arrival_time, departure_time, user):
    """
    Apply time rounding to arrival and departure times based on user settings.
    
    Args:
        arrival_time (datetime): The original arrival time
        departure_time (datetime): The original departure time
        user: The user object
        
    Returns:
        tuple: (rounded_arrival_time, rounded_departure_time)
    """
    interval_minutes, round_to_nearest = get_user_rounding_settings(user)
    
    if interval_minutes == 0:
        return arrival_time, departure_time  # No rounding
    
    # Round arrival time (typically round up to start billing later)
    rounded_arrival = round_time_to_interval(arrival_time, interval_minutes, round_to_nearest)
    
    # Round departure time (typically round up to bill more time)
    rounded_departure = round_time_to_interval(departure_time, interval_minutes, not round_to_nearest)
    
    # Ensure departure is still after arrival
    if rounded_departure <= rounded_arrival:
        # Add one interval to departure time
        rounded_departure = rounded_departure + timedelta(minutes=interval_minutes)
    
    return rounded_arrival, rounded_departure


def format_rounding_interval(interval_minutes):
    """
    Format the rounding interval for display.
    
    Args:
        interval_minutes (int): The interval in minutes
        
    Returns:
        str: Formatted interval description
    """
    if interval_minutes == 0:
        return "No rounding"
    elif interval_minutes == 15:
        return "15 minutes"
    elif interval_minutes == 30:
        return "30 minutes"
    elif interval_minutes == 60:
        return "1 hour"
    else:
        return f"{interval_minutes} minutes"


def get_available_rounding_options():
    """
    Get the available time rounding options.
    
    Returns:
        list: List of tuples (value, label)
    """
    return [
        (0, "No rounding"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "1 hour")
    ]


# Date/Time Formatting Functions

def get_available_date_formats():
    """
    Get the available date format options.
    
    Returns:
        list: List of tuples (value, label, example)
    """
    return [
        ('ISO', 'ISO Format (YYYY-MM-DD)', '2024-12-25'),
        ('US', 'US Format (MM/DD/YYYY)', '12/25/2024'),
        ('EU', 'European Format (DD/MM/YYYY)', '25/12/2024'),
        ('UK', 'UK Format (DD/MM/YYYY)', '25/12/2024'),
        ('Readable', 'Readable Format (Dec 25, 2024)', 'Dec 25, 2024'),
        ('Full', 'Full Format (December 25, 2024)', 'December 25, 2024')
    ]


def format_date_by_preference(dt, date_format='ISO'):
    """
    Format a date according to user preference.
    
    Args:
        dt (datetime): The datetime to format
        date_format (str): The format preference
        
    Returns:
        str: Formatted date string
    """
    if dt is None:
        return ''
    
    format_map = {
        'ISO': '%Y-%m-%d',
        'US': '%m/%d/%Y',
        'EU': '%d/%m/%Y',
        'UK': '%d/%m/%Y',
        'Readable': '%b %d, %Y',
        'Full': '%B %d, %Y'
    }
    
    format_string = format_map.get(date_format, '%Y-%m-%d')
    return dt.strftime(format_string)


def format_time_by_preference(dt, time_format_24h=True):
    """
    Format a time according to user preference.
    
    Args:
        dt (datetime): The datetime to format
        time_format_24h (bool): True for 24h format, False for 12h (AM/PM)
        
    Returns:
        str: Formatted time string
    """
    if dt is None:
        return ''
    
    if time_format_24h:
        return dt.strftime('%H:%M:%S')
    else:
        return dt.strftime('%I:%M:%S %p')


def format_datetime_by_preference(dt, date_format='ISO', time_format_24h=True):
    """
    Format a datetime according to user preferences.
    
    Args:
        dt (datetime): The datetime to format
        date_format (str): The date format preference
        time_format_24h (bool): True for 24h format, False for 12h (AM/PM)
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        return ''
    
    date_part = format_date_by_preference(dt, date_format)
    time_part = format_time_by_preference(dt, time_format_24h)
    return f"{date_part} {time_part}"


def format_time_short_by_preference(dt, time_format_24h=True):
    """
    Format a time without seconds according to user preference.
    
    Args:
        dt (datetime): The datetime to format
        time_format_24h (bool): True for 24h format, False for 12h (AM/PM)
        
    Returns:
        str: Formatted time string (without seconds)
    """
    if dt is None:
        return ''
    
    if time_format_24h:
        return dt.strftime('%H:%M')
    else:
        return dt.strftime('%I:%M %p')


def get_user_format_settings(user):
    """
    Get the date/time format settings for a user.
    
    Args:
        user: The user object
        
    Returns:
        tuple: (date_format, time_format_24h)
    """
    work_config = user.work_config
    if work_config:
        return work_config.date_format or 'ISO', work_config.time_format_24h
    else:
        return 'ISO', True  # Default: ISO date format, 24h time


def format_duration_readable(duration_seconds):
    """
    Format duration in a readable format (e.g., "2h 30m").
    
    Args:
        duration_seconds (int): Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if duration_seconds is None or duration_seconds == 0:
        return '0m'
    
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 and hours == 0:  # Only show seconds if less than an hour
        parts.append(f"{seconds}s")
    
    return ' '.join(parts) if parts else '0m'


def format_duration_decimal(duration_seconds):
    """
    Format duration as decimal hours (e.g., "2.5" for 2h 30m).
    
    Args:
        duration_seconds (int): Duration in seconds
        
    Returns:
        str: Formatted duration as decimal hours
    """
    if duration_seconds is None:
        return '0.00'
    
    hours = duration_seconds / 3600
    return f"{hours:.2f}"