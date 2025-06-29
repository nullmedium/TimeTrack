# Project Time Logging Migration Guide

This document explains how to migrate your TimeTrack database to support the new Project Time Logging feature.

## Overview

The Project Time Logging feature adds the ability to:
- Track time against specific projects
- Manage projects with role-based access control
- Filter and report on project-based time entries
- Export data with project information

## Database Changes

### New Tables
- **`project`**: Stores project information including name, code, description, team assignment, and dates

### Modified Tables
- **`time_entry`**: Added `project_id` (foreign key) and `notes` (text) columns
- **Existing data**: All existing time entries remain unchanged and will show as "No project assigned"

## Migration Options

### Option 1: Run Main Migration Script (Recommended)
The main migration script has been updated to include project functionality:

```bash
python migrate_db.py
```

This will:
- Create the project table
- Add project_id and notes columns to time_entry
- Create 3 sample projects (if no admin user exists)
- Maintain all existing data

### Option 2: Run Project-Specific Migration
For existing installations, you can run the project-specific migration:

```bash
python migrate_projects.py
```

### Option 3: Manual Migration
If you prefer to handle the migration manually, execute these SQL commands:

```sql
-- Create project table
CREATE TABLE project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    code VARCHAR(20) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER NOT NULL,
    team_id INTEGER,
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (created_by_id) REFERENCES user (id),
    FOREIGN KEY (team_id) REFERENCES team (id)
);

-- Add columns to time_entry table
ALTER TABLE time_entry ADD COLUMN project_id INTEGER;
ALTER TABLE time_entry ADD COLUMN notes TEXT;
```

## Sample Projects

The migration creates these sample projects (if admin user exists):

1. **ADMIN001** - General Administration
2. **DEV001** - Development Project  
3. **SUPPORT001** - Customer Support

These can be modified or deleted after migration.

## Rollback

To rollback the project functionality (removes projects but keeps time entry columns):

```bash
python migrate_projects.py rollback
```

**Note**: Due to SQLite limitations, the `project_id` and `notes` columns cannot be removed from the `time_entry` table during rollback.

## Post-Migration Steps

1. **Verify Migration**: Check that the migration completed successfully
2. **Create Projects**: Admin/Supervisor users can create projects via the web interface
3. **Assign Teams**: Optionally assign projects to specific teams
4. **User Training**: Inform users about the new project selection feature

## Migration Verification

After running the migration, verify it worked by:

1. **Check Tables**:
   ```sql
   .tables  -- Should show 'project' table
   .schema project  -- Verify project table structure
   .schema time_entry  -- Verify project_id and notes columns
   ```

2. **Check Web Interface**:
   - Admin/Supervisor users should see "Manage Projects" in their dropdown menu
   - Time tracking interface should show project selection dropdown
   - History page should have project filtering

3. **Check Sample Projects**:
   ```sql
   SELECT * FROM project;  -- Should show 3 sample projects
   ```

## Troubleshooting

### Migration Fails
- Ensure no active connections to the database
- Check file permissions
- Verify admin user exists in the database

### Missing Navigation Links
- Clear browser cache
- Verify user has Admin or Supervisor role
- Check that the templates have been updated

### Project Selection Not Available
- Verify migration completed successfully
- Check that active projects exist in the database
- Ensure user has permission to access projects

## Feature Access

### Admin Users
- Create, edit, delete, and manage all projects
- Access project management interface
- View all project reports

### Supervisor Users  
- Create, edit, and manage projects
- Access project management interface
- View project reports

### Team Leader Users
- View team hours with project breakdown
- No project creation/management access

### Team Member Users
- Select projects when tracking time
- View personal history with project filtering
- No project management access

## File Changes

The migration affects these files:
- `migrate_db.py` - Updated main migration script
- `migrate_projects.py` - New project-specific migration
- `models.py` - Added Project model and updated TimeEntry
- `app.py` - Added project routes and updated existing routes
- Templates - Updated with project functionality
- `static/js/script.js` - Updated time tracking JavaScript

## Backup Recommendation

Before running any migration, it's recommended to backup your database:

```bash
cp timetrack.db timetrack.db.backup
```

This allows you to restore the original database if needed.