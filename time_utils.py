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