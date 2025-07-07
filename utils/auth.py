"""
Authentication utility functions
"""

from flask import g
from models import Role


def is_system_admin(user=None):
    """Helper function to check if user is system admin"""
    if user is None:
        user = g.user
    return user and user.role == Role.SYSTEM_ADMIN


def can_access_system_settings(user=None):
    """Helper function to check if user can access system-wide settings"""
    return is_system_admin(user)