"""
System settings utility functions
"""

from models import SystemSettings


def get_system_setting(key, default='false'):
    """Helper function to get system setting value"""
    setting = SystemSettings.query.filter_by(key=key).first()
    return setting.value if setting else default