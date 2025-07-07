"""
Form validation utility functions
"""

from datetime import datetime
from flask import flash


class ValidationError:
    """Container for validation errors"""
    def __init__(self):
        self.errors = []
    
    def add(self, message):
        """Add an error message"""
        self.errors.append(message)
    
    def has_errors(self):
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def get_first(self):
        """Get the first error message"""
        return self.errors[0] if self.errors else None
    
    def flash_first(self, category='error'):
        """Flash the first error message"""
        if self.errors:
            flash(self.errors[0], category)


def validate_required(value, field_name):
    """Validate that a field is not empty"""
    if not value or (isinstance(value, str) and not value.strip()):
        return f"{field_name} is required"
    return None


def validate_unique(model, field_name, value, company_id=None, exclude_id=None):
    """Validate that a value is unique in the database
    
    Args:
        model: The SQLAlchemy model class
        field_name: The field to check for uniqueness
        value: The value to check
        company_id: Optional company ID for company-scoped uniqueness
        exclude_id: Optional ID to exclude (for updates)
    
    Returns:
        Error message if not unique, None otherwise
    """
    query = model.query.filter_by(**{field_name: value})
    
    if company_id is not None:
        query = query.filter_by(company_id=company_id)
    
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    
    if query.first():
        return f"{field_name.replace('_', ' ').title()} already exists"
    
    return None


def validate_date_range(start_date, end_date, start_name="Start date", end_name="End date"):
    """Validate that start date is before or equal to end date"""
    if start_date and end_date and start_date > end_date:
        return f"{start_name} cannot be after {end_name}"
    return None


def parse_date(date_string, format='%Y-%m-%d'):
    """Parse a date string and return date object or None
    
    Returns:
        tuple: (date_object, error_message)
    """
    if not date_string:
        return None, None
    
    try:
        return datetime.strptime(date_string, format).date(), None
    except ValueError:
        return None, f"Invalid date format (expected {format})"


def parse_datetime(datetime_string, format='%Y-%m-%dT%H:%M'):
    """Parse a datetime string and return datetime object or None
    
    Returns:
        tuple: (datetime_object, error_message)
    """
    if not datetime_string:
        return None, None
    
    try:
        return datetime.strptime(datetime_string, format), None
    except ValueError:
        return None, f"Invalid datetime format (expected {format})"


class FormValidator:
    """Helper class for form validation"""
    
    def __init__(self):
        self.errors = ValidationError()
    
    def validate_required(self, value, field_name):
        """Validate required field and add error if invalid"""
        error = validate_required(value, field_name)
        if error:
            self.errors.add(error)
        return error is None
    
    def validate_unique(self, model, field_name, value, **kwargs):
        """Validate unique field and add error if invalid"""
        error = validate_unique(model, field_name, value, **kwargs)
        if error:
            self.errors.add(error)
        return error is None
    
    def validate_date_range(self, start_date, end_date, **kwargs):
        """Validate date range and add error if invalid"""
        error = validate_date_range(start_date, end_date, **kwargs)
        if error:
            self.errors.add(error)
        return error is None
    
    def parse_date(self, date_string, field_name="Date", **kwargs):
        """Parse date and add error if invalid"""
        date_obj, error = parse_date(date_string, **kwargs)
        if error:
            self.errors.add(f"{field_name}: {error}")
        return date_obj
    
    def parse_datetime(self, datetime_string, field_name="Date/Time", **kwargs):
        """Parse datetime and add error if invalid"""
        datetime_obj, error = parse_datetime(datetime_string, **kwargs)
        if error:
            self.errors.add(f"{field_name}: {error}")
        return datetime_obj
    
    def is_valid(self):
        """Check if form is valid (no errors)"""
        return not self.errors.has_errors()
    
    def flash_errors(self, category='error'):
        """Flash all error messages"""
        for error in self.errors.errors:
            flash(error, category)