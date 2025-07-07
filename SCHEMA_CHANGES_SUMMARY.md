# Database Schema Changes Summary

This document summarizes all database schema changes between commit 4214e88 and the current state of the TimeTrack application.

## Architecture Changes

### 1. **Model Structure Refactoring**
- **Before**: Single monolithic `models.py` file containing all models
- **After**: Models split into domain-specific modules:
  - `models/__init__.py` - Package initialization
  - `models/base.py` - Base model definitions
  - `models/company.py` - Company-related models
  - `models/user.py` - User-related models
  - `models/project.py` - Project-related models
  - `models/task.py` - Task-related models
  - `models/time_entry.py` - Time entry model
  - `models/sprint.py` - Sprint model
  - `models/team.py` - Team model
  - `models/system.py` - System settings models
  - `models/announcement.py` - Announcement model
  - `models/dashboard.py` - Dashboard-related models
  - `models/work_config.py` - Work configuration model
  - `models/invitation.py` - Company invitation model
  - `models/enums.py` - All enum definitions

## New Tables Added

### 1. **company_invitation** (NEW)
- Purpose: Email-based company registration invitations
- Columns:
  - `id` (INTEGER, PRIMARY KEY)
  - `company_id` (INTEGER, FOREIGN KEY → company.id)
  - `email` (VARCHAR(120), NOT NULL)
  - `token` (VARCHAR(64), UNIQUE, NOT NULL)
  - `role` (VARCHAR(50), DEFAULT 'Team Member')
  - `invited_by_id` (INTEGER, FOREIGN KEY → user.id)
  - `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
  - `expires_at` (TIMESTAMP, NOT NULL)
  - `accepted` (BOOLEAN, DEFAULT FALSE)
  - `accepted_at` (TIMESTAMP)
  - `accepted_by_user_id` (INTEGER, FOREIGN KEY → user.id)
- Indexes:
  - `idx_invitation_token` on token
  - `idx_invitation_email` on email
  - `idx_invitation_company` on company_id
  - `idx_invitation_expires` on expires_at

## Modified Tables

### 1. **company**
- Added columns:
  - `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP) - NEW

### 2. **user**
- Added columns:
  - `two_factor_enabled` (BOOLEAN, DEFAULT FALSE) - NEW
  - `two_factor_secret` (VARCHAR(32), NULLABLE) - NEW
  - `avatar_url` (VARCHAR(255), NULLABLE) - NEW

### 3. **user_preferences**
- Added columns:
  - `theme` (VARCHAR(20), DEFAULT 'light')
  - `language` (VARCHAR(10), DEFAULT 'en')
  - `timezone` (VARCHAR(50), DEFAULT 'UTC')
  - `date_format` (VARCHAR(20), DEFAULT 'YYYY-MM-DD')
  - `time_format` (VARCHAR(10), DEFAULT '24h')
  - `email_notifications` (BOOLEAN, DEFAULT TRUE)
  - `email_daily_summary` (BOOLEAN, DEFAULT FALSE)
  - `email_weekly_summary` (BOOLEAN, DEFAULT TRUE)
  - `default_project_id` (INTEGER, FOREIGN KEY → project.id)
  - `timer_reminder_enabled` (BOOLEAN, DEFAULT TRUE)
  - `timer_reminder_interval` (INTEGER, DEFAULT 60)
  - `dashboard_layout` (JSON, NULLABLE)

### 4. **user_dashboard**
- Added columns:
  - `layout` (JSON, NULLABLE) - Alternative grid layout configuration
  - `is_locked` (BOOLEAN, DEFAULT FALSE) - Prevent accidental changes

### 5. **company_work_config**
- Added columns:
  - `standard_hours_per_day` (FLOAT, DEFAULT 8.0)
  - `standard_hours_per_week` (FLOAT, DEFAULT 40.0)
  - `overtime_enabled` (BOOLEAN, DEFAULT TRUE)
  - `overtime_rate` (FLOAT, DEFAULT 1.5)
  - `double_time_enabled` (BOOLEAN, DEFAULT FALSE)
  - `double_time_threshold` (FLOAT, DEFAULT 12.0)
  - `double_time_rate` (FLOAT, DEFAULT 2.0)
  - `require_breaks` (BOOLEAN, DEFAULT TRUE)
  - `break_duration_minutes` (INTEGER, DEFAULT 30)
  - `break_after_hours` (FLOAT, DEFAULT 6.0)
  - `weekly_overtime_threshold` (FLOAT, DEFAULT 40.0)
  - `weekly_overtime_rate` (FLOAT, DEFAULT 1.5)

### 6. **company_settings**
- Added columns:
  - `work_week_start` (INTEGER, DEFAULT 1)
  - `work_days` (VARCHAR(20), DEFAULT '1,2,3,4,5')
  - `allow_overlapping_entries` (BOOLEAN, DEFAULT FALSE)
  - `require_project_for_time_entry` (BOOLEAN, DEFAULT TRUE)
  - `allow_future_entries` (BOOLEAN, DEFAULT FALSE)
  - `max_hours_per_entry` (FLOAT, DEFAULT 24.0)
  - `enable_tasks` (BOOLEAN, DEFAULT TRUE)
  - `enable_sprints` (BOOLEAN, DEFAULT FALSE)
  - `enable_client_access` (BOOLEAN, DEFAULT FALSE)
  - `notify_on_overtime` (BOOLEAN, DEFAULT TRUE)
  - `overtime_threshold_daily` (FLOAT, DEFAULT 8.0)
  - `overtime_threshold_weekly` (FLOAT, DEFAULT 40.0)

### 7. **dashboard_widget**
- Added columns:
  - `config` (JSON) - Widget-specific configuration
  - `is_visible` (BOOLEAN, DEFAULT TRUE)

## Enum Changes

### 1. **WorkRegion** enum
- Added value:
  - `GERMANY = "Germany"` - NEW

### 2. **TaskStatus** enum
- Added value:
  - `ARCHIVED = "Archived"` - NEW

### 3. **WidgetType** enum
- Expanded with many new widget types:
  - Time Tracking: `CURRENT_TIMER`, `DAILY_SUMMARY`, `WEEKLY_CHART`, `BREAK_REMINDER`, `TIME_SUMMARY`
  - Project Management: `ACTIVE_PROJECTS`, `PROJECT_PROGRESS`, `PROJECT_ACTIVITY`, `PROJECT_DEADLINES`, `PROJECT_STATUS`
  - Task Management: `ASSIGNED_TASKS`, `TASK_PRIORITY`, `TASK_CALENDAR`, `UPCOMING_TASKS`, `TASK_LIST`
  - Sprint: `SPRINT_OVERVIEW`, `SPRINT_BURNDOWN`, `SPRINT_PROGRESS`
  - Team & Analytics: `TEAM_WORKLOAD`, `TEAM_PRESENCE`, `TEAM_ACTIVITY`
  - Performance: `PRODUCTIVITY_STATS`, `TIME_DISTRIBUTION`, `PERSONAL_STATS`
  - Actions: `QUICK_ACTIONS`, `RECENT_ACTIVITY`

## Migration Requirements

### PostgreSQL Migration Steps:

1. **Add company_invitation table** (migration 19)
2. **Add updated_at to company table** (migration 20)
3. **Add new columns to user table** for 2FA and avatar
4. **Add new columns to user_preferences table**
5. **Add new columns to user_dashboard table**
6. **Add new columns to company_work_config table**
7. **Add new columns to company_settings table**
8. **Add new columns to dashboard_widget table**
9. **Update enum types** for WorkRegion and TaskStatus
10. **Update WidgetType enum** with new values

### Data Migration Considerations:

1. **Default values**: All new columns have appropriate defaults
2. **Nullable fields**: Most new fields are nullable or have defaults
3. **Foreign keys**: New invitation table has proper FK constraints
4. **Indexes**: Performance indexes added for invitation lookups
5. **Enum migrations**: Need to handle enum type changes carefully in PostgreSQL

### Breaking Changes:

- None identified - all changes are additive or have defaults

### Rollback Strategy:

1. Drop new tables (company_invitation)
2. Drop new columns from existing tables
3. Revert enum changes (remove new values)

## Summary

The main changes involve:
1. Adding email invitation functionality with a new table
2. Enhancing user features with 2FA and avatars
3. Expanding dashboard and widget capabilities
4. Adding comprehensive work configuration options
5. Better tracking with updated_at timestamps
6. Regional compliance support with expanded WorkRegion enum