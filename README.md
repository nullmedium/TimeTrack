# TimeTrack

TimeTrack is a comprehensive web-based time tracking application built with Flask that provides enterprise-level time management capabilities for teams and organizations. The application features role-based access control, project management, team collaboration, and secure authentication.

## Features

### Core Time Tracking
- **Real-time Time Tracking**: Clock in/out with live timer functionality
- **Project Time Logging**: Track time spent on specific projects with project codes
- **Break Management**: Configurable mandatory and additional break tracking
- **Time Entry Management**: Edit, delete, and view time entries with complete history
- **Automatic Calculations**: Duration calculations for work hours and breaks

### User Management & Security
- **Two-Factor Authentication (2FA)**: TOTP-based authentication with QR codes
- **Role-Based Access Control**: Admin, Supervisor, Team Leader, and Team Member roles
- **User Administration**: Create, edit, block/unblock users with verification system
- **Profile Management**: Update email, password, and personal settings

### Team & Project Management
- **Team Management**: Create teams, assign members, and track team hours
- **Project Management**: Create projects with codes, assign to teams, set active/inactive status
- **Team Hours Tracking**: View team member working hours with date filtering
- **Project Assignment**: Flexible project-team assignments and access control

### Export & Reporting
- **Multiple Export Formats**: CSV and Excel export capabilities
- **Individual Time Export**: Personal time entries with date range selection
- **Team Hours Export**: Export team member hours with filtering options
- **Quick Export Options**: Today, week, month, or all-time data exports

### Administrative Features
- **Admin Dashboard**: System overview with user, team, and activity statistics
- **System Settings**: Configure registration settings and global preferences
- **User Administration**: Complete user lifecycle management
- **Team & Project Administration**: Full CRUD operations for teams and projects

## Tech Stack

- **Backend**: Flask 2.0.1 with SQLAlchemy ORM
- **Database**: SQLite with comprehensive relational schema
- **Authentication**: Flask session management with 2FA support
- **Frontend**: Responsive HTML, CSS, JavaScript with real-time updates
- **Security**: TOTP-based two-factor authentication, role-based access control
- **Export**: CSV and Excel export capabilities
- **Dependencies**: See Pipfile for complete dependency list

## Installation

### Prerequisites

- Python 3.12
- pip or pipenv

### Setup with pipenv (recommended)

```bash
# Clone the repository
git clone https://github.com/nullmedium/TimeTrack.git
cd TimeTrack

# Install dependencies using pipenv
pipenv install

# Activate the virtual environment
pipenv shell

# Run the application (migrations run automatically on first startup)
python app.py
```

### First-Time Setup

1. **Start the Application**: The database is automatically created and initialized on first startup
2. **Admin Account**: An initial admin user is created automatically with username `admin` and password `admin`
3. **Change Default Password**: **IMPORTANT**: Change the default admin password immediately after first login
4. **System Configuration**: Access Admin Dashboard to configure system settings
5. **Team Setup**: Create teams and assign team leaders
6. **Project Creation**: Set up projects with codes and team assignments
7. **User Management**: Add users and assign appropriate roles

### Database Migrations

**Automatic Migration System**: All database migrations now run automatically when the application starts. No manual migration scripts need to be run.

The integrated migration system handles:
- Database schema creation for new installations
- Automatic schema updates for existing databases
- User table enhancements (verification, roles, teams, 2FA)
- Project and team management table creation
- Sample data initialization
- Data integrity maintenance during upgrades

**Legacy Migration Files**: The following files are maintained for reference but are no longer needed:
- `migrate_db.py`: Legacy core database migration (now integrated)
- `migrate_roles_teams.py`: Legacy role and team migration (now integrated)
- `migrate_projects.py`: Legacy project migration (now integrated)
- `repair_roles.py`: Legacy role repair utility (functionality now integrated)

### Configuration

The application can be configured through:
- **Admin Dashboard**: System-wide settings and user management
- **User Profiles**: Individual work hour and break preferences
- **Environment Variables**: Database and Flask configuration

## Usage

### For Regular Users
1. **Register/Login**: Create account or log in with existing credentials
2. **Setup 2FA**: Optionally enable two-factor authentication for enhanced security
3. **Clock In/Out**: Use the timer interface to track work hours
4. **Manage Breaks**: Record and track break periods
5. **View History**: Access complete time entry history with filtering
6. **Export Data**: Download time entries in CSV or Excel format

### For Team Leaders
1. **Manage Team Members**: View team member status and activity
2. **Track Team Hours**: Monitor team working hours with date filtering
3. **Export Team Data**: Generate team hour reports

### For Supervisors/Admins
1. **User Management**: Create, edit, and manage user accounts
2. **Team Administration**: Create teams and assign members
3. **Project Management**: Set up projects and assign to teams
4. **System Configuration**: Configure global settings and permissions
5. **Analytics**: View system-wide statistics and activity

## Security Features

- **Two-Factor Authentication**: TOTP-based 2FA with QR code setup
- **Role-Based Access Control**: Four distinct user roles with appropriate permissions
- **Session Management**: Secure login/logout with "remember me" functionality
- **Data Validation**: Comprehensive input validation and error handling
- **Account Verification**: Email verification system for new accounts

## API Endpoints

The application provides various endpoints for different user roles:
- `/admin/*`: Administrative functions (Admin only)
- `/supervisor/*`: Supervisor functions (Supervisor+ roles)
- `/team/*`: Team management (Team Leader+ roles)
- `/export/*`: Data export functionality
- `/auth/*`: Authentication and profile management

## File Structure

- `app.py`: Main Flask application
- `models.py`: Database models and relationships
- `templates/`: HTML templates for all pages
- `static/`: CSS and JavaScript files
- `migrate_*.py`: Database migration scripts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
