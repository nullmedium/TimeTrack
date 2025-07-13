# Flask-Migrate Troubleshooting Guide

## Common Issues and Solutions

### 0. Baseline Script Fails - "Could not extract models/"

**Error**: When running `establish_baseline_4214e88.py`:
```
⚠️ Could not extract models/__init__.py
⚠️ Could not extract models/base.py
```

**Cause**: Commit 4214e88 uses a single `models.py` file, not the modular `models/` directory.

**Solution**:
```bash
# For local development with Git:
python simple_baseline_4214e88.py

# For Docker deployments (no Git):
python docker_migrate_init.py
```

### 1. "Target database is not up to date"

**Error**: When running `flask db migrate`, you get:
```
ERROR [flask_migrate] Target database is not up to date.
```

**Solution**:
```bash
# Apply pending migrations first
flask db upgrade

# Then create new migration
flask db migrate -m "Your changes"
```

### 2. "No changes in schema detected"

**Possible Causes**:
1. No actual model changes were made
2. Model not imported in `models/__init__.py`
3. Database already has the changes

**Solutions**:
```bash
# Check what Flask-Migrate sees
flask db compare

# Force detection by editing a model slightly
# (add a comment, save, then remove it)

# Check current state
python diagnose_migrations.py
```

### 3. After First Migration, Second One Fails

**This is the most common issue!**

After creating the baseline migration, you must apply it before creating new ones:

```bash
# Sequence:
flask db migrate -m "Initial migration"  # Works ✓
flask db migrate -m "Add new column"     # Fails ✗

# Fix:
flask db upgrade                         # Apply first migration
flask db migrate -m "Add new column"     # Now works ✓
```

### 4. Import Errors

**Error**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Ensure FLASK_APP is set
export FLASK_APP=app.py

# Check imports
python -c "from app import app, db; print('OK')"
```

### 5. PostgreSQL Enum Issues

**Error**: Cannot add new enum value in migration

**Solution**: Edit the generated migration file:
```python
def upgrade():
    # Instead of using Enum type directly
    # Use raw SQL for PostgreSQL enums
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'NEW_VALUE'")
```

### 6. Migration Conflicts After Git Pull

**Error**: Conflicting migration heads

**Solution**:
```bash
# Merge the migrations
flask db merge -m "Merge migrations"

# Then upgrade
flask db upgrade
```

## Quick Diagnostic Commands

```bash
# Run full diagnostics
python diagnose_migrations.py

# Fix sequence issues
python fix_migration_sequence.py

# Check current state
flask db current     # Current DB revision
flask db heads       # Latest file revision
flask db history     # All migrations

# Compare DB with models
flask db compare     # Shows differences
```

## Best Practices to Avoid Issues

1. **Always upgrade before new migrations**:
   ```bash
   flask db upgrade
   flask db migrate -m "New changes"
   ```

2. **Review generated migrations**:
   - Check `migrations/versions/` folder
   - Look for DROP commands you didn't intend

3. **Test on development first**:
   ```bash
   # Test the migration
   flask db upgrade
   
   # Test rollback
   flask db downgrade
   ```

4. **Handle enums carefully**:
   - PostgreSQL enums need special handling
   - Consider using String columns instead

5. **Commit migrations with code**:
   - Always commit migration files with model changes
   - This keeps database and code in sync

## Revision Mismatch Errors

### "Can't locate revision identified by 'xxxxx'"

This means your database thinks it's at a revision that doesn't exist in your migration files.

**Quick Fix**:
```bash
# Run the automated fix
./quick_fix_revision.sh

# Or manually:
# 1. Find your latest migration
ls migrations/versions/*.py

# 2. Get the revision from the file
grep "revision = " migrations/versions/latest_file.py

# 3. Stamp database to that revision
flask db stamp <revision_id>
```

**Detailed Diagnosis**:
```bash
python fix_revision_mismatch.py
```

## Emergency Fixes

### Reset Migration State (Development Only!)

```bash
# Remove migrations and start over
rm -rf migrations
python establish_baseline_4214e88.py
flask db stamp head
```

### Force Database to Current State

```bash
# Mark database as up-to-date without running migrations
flask db stamp head

# Or stamp to specific revision
flask db stamp <revision_id>
```

### Manual Migration Edit

Sometimes you need to edit the generated migration:

1. Generate migration: `flask db migrate -m "Changes"`
2. Edit file in `migrations/versions/`
3. Test with: `flask db upgrade`
4. Test rollback: `flask db downgrade`

## Getting Help

If these solutions don't work:

1. Run diagnostics: `python diagnose_migrations.py`
2. Check the full error message
3. Look at the generated SQL: `flask db upgrade --sql`
4. Check Flask-Migrate logs in detail