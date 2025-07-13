# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TimeTrack is a comprehensive web-based time tracking application built with Flask that provides enterprise-level time management capabilities for teams and organizations. It features multi-tenancy, role-based access control, project/team management, billing/invoicing, and secure authentication with 2FA.

## Tech Stack

- **Backend**: Flask 2.0.1 with SQLAlchemy ORM
- **Database**: PostgreSQL (production) / SQLite (development)
- **Migrations**: Flask-Migrate (Alembic-based)
- **Frontend**: Server-side rendered Jinja2 templates with vanilla JavaScript
- **Authentication**: Session-based with TOTP 2FA support and password reset via email
- **Export**: Pandas for CSV/Excel, ReportLab for PDF generation
- **Mobile**: Progressive Web App (PWA) support with optimized mobile UI

## Development Setup

### Local Development

```bash
# Using virtual environment
source .venv/bin/activate  # or pipenv shell

# Set environment variables (PostgreSQL example)
export DATABASE_URL="postgresql://timetrack:timetrack123@localhost:5432/timetrack"

# Run the application
python app.py
```

### Docker Development

```bash
# Standard docker-compose (uses PostgreSQL)
docker-compose up

# Debug mode with hot-reload
docker-compose -f docker-compose.debug.yml up
```

## Database Operations

### Flask-Migrate Commands

```bash
# Create a new migration
python create_migration.py "Description of changes"

# Apply pending migrations
python apply_migration.py

# Check current migration state
python check_migration_state.py

# Clean migration state (CAUTION: destructive)
python clean_migration_state.py

# For Docker environments
docker exec timetrack-timetrack-1 python create_migration.py "Description"
docker exec timetrack-timetrack-1 python apply_migration.py
```

### Standard Flask-Migrate Commands

```bash
# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback one revision
flask db downgrade

# Show current revision
flask db current

# Show migration history
flask db history
```

## Key Architecture Patterns

### 1. Blueprint-Based Modular Architecture

Routes are organized into blueprints by feature domain:
- `/routes/auth.py` - Authentication and authorization decorators
- `/routes/projects.py` - Project management
- `/routes/invoice.py` - Billing and invoicing
- `/routes/tax_configuration.py` - Tax management
- `/routes/teams.py` - Team management
- `/routes/export.py` - Data export functionality

### 2. Model Organization

Models are split by domain in `/models/`:
- `user.py` - User, Role, UserPreferences
- `company.py` - Company, CompanySettings, CompanyWorkConfig
- `project.py` - Project, ProjectCategory
- `team.py` - Team
- `time_entry.py` - TimeEntry
- `invoice.py` - Invoice, InvoiceLineItem, InvoiceStatus
- `tax_configuration.py` - TaxConfiguration
- `enums.py` - BillingType, AccountType, etc.

### 3. Multi-Tenancy Pattern

All data is scoped by company_id with automatic filtering:
```python
# Common pattern in routes
projects = Project.query.filter_by(company_id=g.user.company_id).all()
```

### 4. Role-Based Access Control

Decorators enforce permissions:
```python
@role_required(Role.SUPERVISOR)  # Supervisor and above
@admin_required  # Admin and System Admin only
@company_required  # Ensures user has company context
```

### 5. Billing Architecture

- Projects support multiple billing types: NON_BILLABLE, HOURLY, DAILY_RATE, FIXED_RATE
- Invoices support net/gross pricing with country-specific tax configurations
- TimeEntry calculates billing based on project settings (8-hour day for daily rates)

## Common Development Tasks

### Adding a New Feature

1. Create model in appropriate file under `/models/`
2. Create blueprint in `/routes/` with proper decorators
3. Register blueprint in `app.py`
4. Create templates in `/templates/`
5. Run migration: `python create_migration.py "Add feature X"`

### Testing Database Changes

```bash
# Check what will be migrated
python check_migration_state.py

# Test in isolated environment
docker-compose -f docker-compose.debug.yml up

# Apply to development database
DATABASE_URL="postgresql://..." python apply_migration.py
```

### Working with Billing Features

When modifying billing/invoice features:
1. Check `models/enums.py` for BillingType values
2. Update TimeEntry.calculate_billing_amount() for new billing logic
3. Update Invoice.calculate_totals() for tax calculations
4. Ensure templates handle all billing types (hourly/daily rate display)

## Important Implementation Details

### Session Management
- Sessions are permanent with 7-day lifetime
- User context loaded in `app.before_request()` via `g.user`
- Company context available via `g.company`

### Time Calculations
- Time entries use UTC internally, converted for display
- Rounding rules configured per company/user
- Break time calculations handled in TimeEntry model

### Export System
- Pandas handles CSV/Excel generation
- ReportLab for PDF invoices
- Export routes handle large datasets with streaming

### Email Configuration
- Flask-Mail configured via environment variables
- MAIL_SERVER, MAIL_PORT, MAIL_USERNAME required
- Used for user invitations and password resets

### Authentication Features
- Password reset functionality with secure tokens (1-hour expiry)
- Two-factor authentication (2FA) using TOTP
- Session-based authentication with "Remember Me" option
- Email verification for new accounts (configurable)

### Mobile UI Features
- Progressive Web App (PWA) manifest for installability
- Mobile-optimized navigation with hamburger menu and bottom nav
- Touch-friendly form inputs and buttons (44px minimum touch targets)
- Responsive tables with card view on small screens
- Pull-to-refresh functionality
- Mobile gestures support (swipe, pinch-to-zoom)
- Date/time pickers that respect user preferences

## Environment Variables

Required for production:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Flask session secret
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` - Email config

Optional:
- `FLASK_ENV` - Set to 'development' for debug mode
- `FORCE_HTTPS` - Set to 'true' for HTTPS enforcement
- `TRUST_PROXY_HEADERS` - Set to 'true' when behind reverse proxy

## Troubleshooting

### Migration Issues
1. Run `python check_migration_state.py` to verify database state
2. Check `/migrations/versions/` for migration files
3. If stuck, use `clean_migration_state.py` (careful - destructive)

### Import Errors
- Ensure all model imports in routes use: `from models import ModelName`
- Blueprint registration order matters in `app.py`

### Database Connection
- PostgreSQL requires running container or local instance
- Default fallback to SQLite at `/data/timetrack.db`
- Check `docker-compose.yml` for PostgreSQL credentials