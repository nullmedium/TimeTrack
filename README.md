# TimeTrack

TimeTrack is a comprehensive web-based time tracking application built with Flask that provides enterprise-level time management capabilities for teams and organizations. The application features multi-tenancy support, role-based access control, project management, team collaboration, billing/invoicing, and secure authentication with 2FA and password reset functionality. It includes a Progressive Web App (PWA) interface with mobile-optimized features.

## Features

### Core Time Tracking
- **Real-time Time Tracking**: Clock in/out with live timer functionality
- **Project Time Logging**: Track time spent on specific projects with project codes
- **Break Management**: Configurable mandatory and additional break tracking
- **Time Entry Management**: Edit, delete, and view time entries with complete history
- **Automatic Calculations**: Duration calculations for work hours and breaks

### User Management & Security
- **Two-Factor Authentication (2FA)**: TOTP-based authentication with QR codes
- **Password Reset**: Secure email-based password recovery (1-hour token expiry)
- **Role-Based Access Control**: System Admin, Admin, Supervisor, Team Leader, and Team Member roles
- **Multi-Tenancy**: Complete data isolation between companies
- **User Administration**: Create, edit, block/unblock users with email verification
- **Profile Management**: Update email, password, avatar, and personal settings
- **Company Invitations**: Invite users to join your company via email

### Team & Project Management
- **Team Management**: Create teams, assign members, and track team hours
- **Project Management**: Create projects with codes, categories, billing types (hourly/daily/fixed)
- **Sprint Management**: Agile sprint planning and tracking
- **Task Management**: Create and manage tasks with subtasks and dependencies
- **Notes System**: Create, organize, and share notes with folder structure
- **Team Hours Tracking**: View team member working hours with date filtering
- **Project Assignment**: Flexible project-team assignments and access control

### Export & Reporting
- **Multiple Export Formats**: CSV, Excel, and PDF export capabilities
- **Individual Time Export**: Personal time entries with date range selection
- **Team Hours Export**: Export team member hours with filtering options
- **Invoice Generation**: Create and export invoices with tax configurations
- **Analytics Dashboard**: Visual analytics with charts and statistics
- **Quick Export Options**: Today, week, month, or all-time data exports

### Administrative Features
- **Company Management**: Multi-company support with separate settings
- **Admin Dashboard**: System overview with user, team, and activity statistics
- **System Settings**: Configure registration, email verification, tracking scripts
- **Work Configuration**: Set work hours, break rules, and rounding preferences
- **Tax Configuration**: Country-specific tax rates for invoicing
- **Branding**: Custom logos, colors, and application naming
- **User Administration**: Complete user lifecycle management
- **Team & Project Administration**: Full CRUD operations for teams and projects
- **System Admin Tools**: Multi-company oversight and system health monitoring

## Tech Stack

- **Backend**: Flask 2.0.1 with SQLAlchemy ORM
- **Database**: PostgreSQL (production)
- **Migrations**: Flask-Migrate (Alembic-based) with custom helpers
- **Authentication**: Session-based with 2FA and password reset via Flask-Mail
- **Frontend**: Server-side Jinja2 templates with vanilla JavaScript
- **Mobile**: Progressive Web App (PWA) with mobile-optimized UI
- **Export**: Pandas for CSV/Excel, ReportLab for PDF generation
- **Containerization**: Docker and Docker Compose for easy deployment
- **Dependencies**: See requirements.txt for complete dependency list

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 15+ (for production)
- Docker & Docker Compose (recommended)

### Quick Start with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/nullmedium/TimeTrack.git
cd TimeTrack

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your settings

# Start the application
docker-compose up -d

# Access at http://localhost:5000
```

### Local Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/timetrack"
export SECRET_KEY="your-secret-key"
export MAIL_SERVER="smtp.example.com"
# ... other environment variables

# Run migrations
python create_migration.py "Initial setup"
python apply_migration.py

# Run the application
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

**Flask-Migrate System**: The application uses Flask-Migrate (Alembic-based) for database version control.

```bash
# Create a new migration
python create_migration.py "Description of changes"

# Apply migrations
python apply_migration.py

# Check migration status
python check_migration_state.py

# For Docker environments
docker exec timetrack-timetrack-1 python create_migration.py "Description"
docker exec timetrack-timetrack-1 python apply_migration.py
```

The migration system handles:
- Automatic schema updates on container startup
- PostgreSQL-specific features (enums, constraints)
- Safe rollback capabilities
- Multi-tenancy data isolation
- Preservation of existing data during schema changes

### Configuration

#### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development  # or production

# Email (required for invitations and password reset)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password

# Optional
FORCE_HTTPS=true  # Force HTTPS in production
TRUST_PROXY_HEADERS=true  # When behind reverse proxy
```

#### Application Settings

- **Company Settings**: Work hours, break requirements, time rounding
- **User Preferences**: Date/time formats, timezone, UI preferences
- **System Settings**: Registration, email verification, tracking scripts
- **Branding**: Custom logos, colors, and naming

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
- **Password Reset**: Secure email-based recovery with time-limited tokens
- **Role-Based Access Control**: Five distinct user roles with granular permissions
- **Multi-Tenancy**: Complete data isolation between companies
- **Session Management**: Secure sessions with configurable lifetime
- **Email Verification**: Optional email verification for new accounts
- **Password Strength**: Enforced password complexity requirements
- **Security Headers**: HSTS, CSP, X-Frame-Options, and more
- **Input Validation**: Comprehensive server-side validation
- **CSRF Protection**: Built-in Flask CSRF protection

## Features for Mobile Users

- **Progressive Web App**: Install TimeTrack as an app on mobile devices
- **Mobile Navigation**: Bottom navigation bar and hamburger menu
- **Touch Optimization**: 44px minimum touch targets throughout
- **Responsive Tables**: Automatic card view on small screens
- **Mobile Gestures**: Swipe navigation and pull-to-refresh
- **Date/Time Pickers**: Mobile-friendly pickers respecting user preferences
- **Offline Support**: Basic offline functionality with service workers
- **Performance**: Lazy loading and optimized for mobile networks

## Project Structure

```
TimeTrack/
├── app.py                 # Main Flask application
├── models/               # Database models organized by domain
│   ├── user.py          # User, Role, UserPreferences
│   ├── company.py       # Company, CompanySettings
│   ├── project.py       # Project, ProjectCategory
│   ├── time_entry.py    # TimeEntry model
│   └── ...              # Other domain models
├── routes/              # Blueprint-based route handlers
│   ├── auth.py         # Authentication routes
│   ├── projects.py     # Project management
│   ├── teams.py        # Team management
│   └── ...             # Other route modules
├── templates/           # Jinja2 templates
├── static/             # CSS, JS, images
│   ├── css/           # Stylesheets including mobile
│   ├── js/            # JavaScript including PWA support
│   └── manifest.json  # PWA manifest
├── migrations/         # Flask-Migrate/Alembic migrations
├── docker-compose.yml  # Docker configuration
└── requirements.txt    # Python dependencies
```

## API Endpoints

Key application routes organized by function:
- `/` - Home dashboard
- `/login`, `/logout`, `/register` - Authentication
- `/forgot_password`, `/reset_password/<token>` - Password recovery
- `/time-tracking` - Main time tracking interface
- `/projects/*` - Project management
- `/teams/*` - Team management
- `/tasks/*` - Task and sprint management
- `/notes/*` - Notes system
- `/invoices/*` - Billing and invoicing
- `/export/*` - Data export functionality
- `/admin/*` - Administrative functions
- `/system-admin/*` - System administration (multi-company)

## Deployment

### Production Deployment with Docker

```bash
# Clone and configure
git clone https://github.com/nullmedium/TimeTrack.git
cd TimeTrack
cp .env.example .env
# Edit .env with production values

# Build and start
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f

# Backup database
docker exec timetrack-db-1 pg_dump -U timetrack timetrack > backup.sql
```

### Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 80;
    server_name timetrack.example.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

1. **Migration Errors**
   - Check current state: `python check_migration_state.py`
   - View migration history: `flask db history`
   - Fix revision conflicts in alembic_version table

2. **Docker Issues**
   - Container not starting: `docker logs timetrack-timetrack-1`
   - Database connection: Ensure PostgreSQL is healthy
   - Permission errors: Check volume permissions

3. **Email Not Sending**
   - Verify MAIL_* environment variables
   - Check firewall rules for SMTP port
   - Enable "less secure apps" if using Gmail

4. **2FA Issues**
   - Ensure system time is synchronized
   - QR code not scanning: Check for firewall blocking images

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Write tests for new features
- Update documentation as needed
- Ensure migrations are reversible
- Test on both PostgreSQL and SQLite

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Flask community for the excellent framework
- Contributors and testers
- Open source projects that made this possible
