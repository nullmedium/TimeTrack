"""
Dashboard widget models
"""

from datetime import datetime
import json
from . import db
from .enums import WidgetType, Role


class DashboardWidget(db.Model):
    """User dashboard widget configuration"""
    id = db.Column(db.Integer, primary_key=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('user_dashboard.id'), nullable=False)
    widget_type = db.Column(db.Enum(WidgetType), nullable=False)
    
    # Grid position and size
    grid_x = db.Column(db.Integer, nullable=False, default=0)  # X position in grid
    grid_y = db.Column(db.Integer, nullable=False, default=0)  # Y position in grid
    grid_width = db.Column(db.Integer, nullable=False, default=1)  # Width in grid units
    grid_height = db.Column(db.Integer, nullable=False, default=1)  # Height in grid units
    
    # Widget configuration
    title = db.Column(db.String(100))  # Custom widget title
    config = db.Column(db.Text)  # JSON string for widget-specific configuration
    refresh_interval = db.Column(db.Integer, default=60)  # Refresh interval in seconds
    
    # Widget state
    is_visible = db.Column(db.Boolean, default=True)
    is_minimized = db.Column(db.Boolean, default=False)
    z_index = db.Column(db.Integer, default=1)  # Stacking order
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<DashboardWidget {self.widget_type.value} ({self.grid_width}x{self.grid_height})>'
    
    @property
    def config_dict(self):
        """Parse widget configuration JSON"""
        if self.config:
            try:
                return json.loads(self.config)
            except:
                return {}
        return {}
    
    @config_dict.setter
    def config_dict(self, value):
        """Set widget configuration as JSON"""
        self.config = json.dumps(value) if value else None


class WidgetTemplate(db.Model):
    """Pre-defined widget templates for easy dashboard setup"""
    id = db.Column(db.Integer, primary_key=True)
    widget_type = db.Column(db.Enum(WidgetType), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icon name or emoji
    
    # Default configuration
    default_width = db.Column(db.Integer, default=1)
    default_height = db.Column(db.Integer, default=1)
    default_config = db.Column(db.Text)  # JSON string for default widget configuration
    
    # Access control
    required_role = db.Column(db.Enum(Role), default=Role.TEAM_MEMBER)
    is_active = db.Column(db.Boolean, default=True)
    
    # Categories for organization
    category = db.Column(db.String(50), default='General')  # Time, Projects, Tasks, Analytics, Team, Actions
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<WidgetTemplate {self.name} ({self.widget_type.value})>'
    
    def can_user_access(self, user):
        """Check if user has required role to use this widget"""
        if not self.is_active:
            return False
        
        # Define role hierarchy
        role_hierarchy = {
            Role.TEAM_MEMBER: 1,
            Role.TEAM_LEADER: 2,
            Role.SUPERVISOR: 3,
            Role.ADMIN: 4,
            Role.SYSTEM_ADMIN: 5
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(self.required_role, 0)
        
        return user_level >= required_level