# Post-Baseline Migrations Required

After establishing the baseline at commit `4214e88d18fce7a9c75927753b8d4e9222771e14`, the following schema changes need to be recreated as Flask-Migrate migrations:

## Required Migrations (in order)

### 1. Add company.updated_at
```bash
flask db migrate -m "Add updated_at to company table"
```

Expected changes:
- ADD COLUMN company.updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 2. Add user 2FA and avatar columns
```bash
flask db migrate -m "Add two-factor auth and avatar columns to user"
```

Expected changes:
- ADD COLUMN user.two_factor_enabled BOOLEAN DEFAULT FALSE
- ADD COLUMN user.two_factor_secret VARCHAR(32)
- ADD COLUMN user.avatar_url VARCHAR(255)

### 3. Create company_invitation table
```bash
flask db migrate -m "Create company invitation system"
```

Expected changes:
- CREATE TABLE company_invitation (with all columns as defined in models/invitation.py)
- Note: The current model has slightly different columns than the old migration

### 4. Add user_preferences columns
```bash
flask db migrate -m "Add missing columns to user preferences"
```

Expected changes:
- Multiple columns for theme, language, timezone, notifications, etc.

### 5. Add user_dashboard layout columns
```bash
flask db migrate -m "Add layout and lock columns to user dashboard"
```

Expected changes:
- ADD COLUMN user_dashboard.layout JSON DEFAULT '{}'
- ADD COLUMN user_dashboard.is_locked BOOLEAN DEFAULT FALSE

### 6. Add company_work_config columns
```bash
flask db migrate -m "Add work configuration columns"
```

Expected changes:
- Multiple columns for overtime, rates, thresholds

### 7. Add company_settings columns
```bash
flask db migrate -m "Add company settings columns"
```

Expected changes:
- Multiple columns for work week, time tracking, features

### 8. Add dashboard_widget config columns
```bash
flask db migrate -m "Add widget configuration columns"
```

Expected changes:
- ADD COLUMN dashboard_widget.config JSON DEFAULT '{}'
- ADD COLUMN dashboard_widget.is_visible BOOLEAN DEFAULT TRUE

### 9. Update enums
```bash
# These might need manual migration files
flask db migrate -m "Add GERMANY to WorkRegion enum"
flask db migrate -m "Add ARCHIVED to TaskStatus enum"
flask db migrate -m "Add new WidgetType enum values"
```

### 10. Add note sharing functionality
```bash
flask db migrate -m "Add note sharing tables and columns"
```

Expected changes:
- CREATE TABLE note_share
- ADD COLUMN note.folder VARCHAR(100)
- CREATE TABLE note_folder
- Cascade delete constraints on note_link

### 11. Add time preferences
```bash
flask db migrate -m "Add time formatting preferences"
```

Expected changes:
- ADD COLUMN user_preferences.time_format_24h BOOLEAN DEFAULT TRUE
- ADD COLUMN user_preferences.time_rounding_minutes INTEGER DEFAULT 0
- ADD COLUMN user_preferences.round_to_nearest BOOLEAN DEFAULT FALSE

## Migration Order Script

Create a script to apply all migrations in order:

```bash
#!/bin/bash
# apply_post_baseline_migrations.sh

echo "Applying post-baseline migrations..."

# Mark database at baseline if not already done
flask db stamp head

# Generate and apply each migration
flask db migrate -m "Add updated_at to company table"
flask db upgrade

flask db migrate -m "Add two-factor auth and avatar columns to user"
flask db upgrade

flask db migrate -m "Create company invitation system"
flask db upgrade

# ... continue for all migrations
```

## Manual Migration Adjustments

Some migrations may need manual adjustments:

### PostgreSQL Enums
Edit the generated migration files to add enum values:

```python
def upgrade():
    # For WorkRegion enum
    op.execute("ALTER TYPE workregion ADD VALUE IF NOT EXISTS 'GERMANY'")
    
    # For TaskStatus enum
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")
    
    # For WidgetType enum
    op.execute("ALTER TYPE widgettype ADD VALUE IF NOT EXISTS 'REVENUE_CHART'")
    # ... add other widget types
```

### Foreign Key Constraints
Ensure CASCADE deletes are properly set:

```python
def upgrade():
    # For note_link table
    op.create_foreign_key(
        'note_link_source_note_id_fkey',
        'note_link', 'note',
        ['source_note_id'], ['id'],
        ondelete='CASCADE'
    )
```

## Verification

After applying all migrations:

1. Compare schema with production database
2. Verify all enum values are present
3. Check foreign key constraints
4. Test rollback functionality

## Notes

- Review `migrations_old/postgres_only_migration.py` for the complete list of changes
- Some columns in the old migrations may not exist in current models - skip those
- Always test on development database first
- Keep this document updated as migrations are applied