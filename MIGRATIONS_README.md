# TimeTrack Database Migrations

## Quick Start

### Docker Deployments
```bash
# Automatic: startup scripts handle everything
# Manual: python docker_migrate_init.py
```
See `DOCKER_MIGRATIONS_GUIDE.md` for details.

### Local Development
```bash
# With Git history:
python simple_baseline_4214e88.py

# Without Git history:
python docker_migrate_init.py
```

## Documentation Structure

1. **FLASK_MIGRATE_GUIDE.md** - Complete Flask-Migrate documentation
2. **DOCKER_MIGRATIONS_GUIDE.md** - Docker-specific instructions
3. **FLASK_MIGRATE_TROUBLESHOOTING.md** - Common issues and solutions
4. **POST_BASELINE_MIGRATIONS.md** - Required migrations after baseline
5. **MIGRATION_QUICK_REFERENCE.md** - Command cheat sheet

## Key Scripts

### For Docker (No Git Required)
- `docker_migrate_init.py` - Initialize from current schema
- `migrate.sh` - Helper script (created by docker_migrate_init.py)

### For Development (Git Required)
- `simple_baseline_4214e88.py` - Initialize from commit 4214e88
- `establish_baseline_4214e88.py` - Advanced baseline setup

### Troubleshooting
- `diagnose_migrations.py` - Comprehensive diagnostics
- `fix_migration_sequence.py` - Fix sequence issues
- `fix_revision_mismatch.py` - Fix revision errors
- `quick_fix_revision.sh` - Quick revision fix

## Common Workflows

### First Deployment (Docker)
Handled automatically by startup scripts, or:
```bash
python docker_migrate_init.py
flask db stamp head  # For existing DB
flask db upgrade     # For new DB
```

### Create New Migration
```bash
flask db migrate -m "Add user preferences"
flask db upgrade
```

### Check Status
```bash
flask db current   # Current revision
flask db history   # All migrations
./migrate.sh status  # In Docker
```

## Important Notes

1. **Docker containers don't have Git** - Use docker_migrate_init.py
2. **Always review generated migrations** before applying
3. **Test on staging first** before production
4. **Include migrations/ in Docker image** or use volume mount
5. **Startup scripts handle initialization** automatically

Choose the appropriate guide based on your deployment environment!