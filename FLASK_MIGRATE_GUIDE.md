# Flask-Migrate Migration Guide

## Overview

TimeTrack has been refactored to use Flask-Migrate (which wraps Alembic) for database migrations instead of manual SQL scripts. This provides automatic migration generation, version control, and rollback capabilities.

**IMPORTANT**: The baseline for Flask-Migrate is set at git commit `4214e88d18fce7a9c75927753b8d4e9222771e14`. All schema changes after this commit need to be recreated as Flask-Migrate migrations.

**For Docker Deployments**: See `DOCKER_MIGRATIONS_GUIDE.md` for Docker-specific instructions (no Git required).

## Migration from Old System

### For Existing Deployments

If you have an existing database with the old migration system:

```bash
# 1. Install new dependencies
pip install -r requirements.txt

# 2. Establish baseline from commit 4214e88
python simple_baseline_4214e88.py
# Note: Use simple_baseline_4214e88.py as it handles the models.py transition correctly

# 3. Mark your database as being at the baseline
flask db stamp head

# 4. Apply any post-baseline migrations
# Review migrations_old/postgres_only_migration.py for changes after 4214e88
# Create new migrations for each feature:
flask db migrate -m "Add company updated_at column"
flask db migrate -m "Add user 2FA columns"
flask db migrate -m "Add company invitation table"
# etc...
```

### For New Deployments

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize and create database
python manage_migrations.py init
python manage_migrations.py apply
```

## Daily Usage

### Creating Migrations

When you modify models (add columns, tables, etc.):

```bash
# Generate migration automatically
flask db migrate -m "Add user avatar field"

# Or use the helper script
python manage_migrations.py create -m "Add user avatar field"
```

**Always review the generated migration** in `migrations/versions/` before applying!

### Applying Migrations

```bash
# Apply all pending migrations
flask db upgrade

# Or use the helper script
python manage_migrations.py apply
```

### Rolling Back

```bash
# Rollback one migration
flask db downgrade

# Or use the helper script
python manage_migrations.py rollback
```

### Viewing Status

```bash
# Current migration version
flask db current

# Migration history
flask db history

# Or use the helper script
python manage_migrations.py history
```

## Important Considerations

### 1. PostgreSQL Enums

Flask-Migrate may not perfectly handle PostgreSQL enum types. When adding new enum values:

```python
# In the migration file, you may need to add:
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new enum value
    op.execute("ALTER TYPE taskstatus ADD VALUE 'NEW_STATUS'")
```

### 2. Data Migrations

For complex data transformations, add custom code to migration files:

```python
def upgrade():
    # Schema changes
    op.add_column('user', sa.Column('new_field', sa.String()))
    
    # Data migration
    connection = op.get_bind()
    result = connection.execute('SELECT id, old_field FROM user')
    for row in result:
        connection.execute(
            f"UPDATE user SET new_field = '{process(row.old_field)}' WHERE id = {row.id}"
        )
```

### 3. Production Deployments

The startup scripts have been updated to automatically run migrations:

```bash
# startup_postgres.sh now includes:
flask db upgrade
```

### 4. Development Workflow

1. Pull latest code
2. Run `flask db upgrade` to apply any new migrations
3. Make your model changes
4. Run `flask db migrate -m "Description"`
5. Review the generated migration
6. Test with `flask db upgrade`
7. Commit both model changes and migration file

## Troubleshooting

### "Target database is not up to date"

```bash
# Check current version
flask db current

# Force upgrade
flask db stamp head  # Mark as latest without running
flask db upgrade     # Apply any pending
```

### "Can't locate revision"

Your database revision doesn't match any migration file. This happens when switching branches.

```bash
# See all migrations
flask db history

# Stamp to a specific revision
flask db stamp <revision_id>
```

### Migration Conflicts

When multiple developers create migrations:

1. Merge the migration files carefully
2. Update the `down_revision` in the newer migration
3. Test thoroughly

## Best Practices

1. **One migration per feature** - Don't bundle unrelated changes
2. **Descriptive messages** - Use clear migration messages
3. **Review before applying** - Always check generated SQL
4. **Test rollbacks** - Ensure downgrade() works
5. **Backup before major migrations** - Especially in production

## Migration File Structure

```
migrations/
├── README.md          # Quick reference
├── alembic.ini       # Alembic configuration
├── env.py            # Migration environment
├── script.py.mako    # Migration template
└── versions/         # Migration files
    ├── 001_initial_migration.py
    ├── 002_add_user_avatars.py
    └── ...
```

## Helper Scripts

- `manage_migrations.py` - Simplified migration management
- `migrate_to_alembic.py` - One-time transition from old system
- `init_migrations.py` - Quick initialization script

## Environment Variables

```bash
# Required for migrations
export FLASK_APP=app.py
export DATABASE_URL=postgresql://user:pass@host/db
```

## References

- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)