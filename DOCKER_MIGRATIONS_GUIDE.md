# Flask-Migrate in Docker Deployments

## Overview

Docker containers typically don't include Git repositories, so we can't use Git commands to extract historical schemas. This guide explains how to use Flask-Migrate in Docker environments.

## Initial Setup (First Deployment)

When deploying with Flask-Migrate for the first time:

### Automatic Setup (via startup scripts)

The `startup.sh` and `startup_postgres.sh` scripts now automatically handle migration initialization:

1. **For existing databases with data:**
   - Creates a baseline migration from current models
   - Stamps the database as current (no changes applied)
   - Ready for future migrations

2. **For empty databases:**
   - Creates a baseline migration from current models
   - Applies it to create all tables
   - Ready for future migrations

### Manual Setup

If you need to set up manually:

```bash
# Inside your Docker container
python docker_migrate_init.py

# For existing database with tables:
flask db stamp head

# For new empty database:
flask db upgrade
```

## Creating New Migrations

After initial setup, create new migrations normally:

```bash
# 1. Make changes to your models

# 2. Generate migration
flask db migrate -m "Add user preferences"

# 3. Review the generated migration
cat migrations/versions/*.py

# 4. Apply the migration
flask db upgrade
```

## Helper Script

The `docker_migrate_init.py` script creates a `migrate.sh` helper:

```bash
# Check current migration status
./migrate.sh status

# Apply pending migrations
./migrate.sh apply

# Create new migration
./migrate.sh create "Add company settings"

# Mark database as current (existing DBs)
./migrate.sh mark-current
```

## Docker Compose Example

```yaml
version: '3.8'
services:
  web:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/timetrack
      - FLASK_APP=app.py
    volumes:
      # Persist migrations between container restarts
      - ./migrations:/app/migrations
    depends_on:
      - db
    command: ./startup_postgres.sh

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=timetrack
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Important Notes

### 1. Migrations Directory

- The `migrations/` directory should be persisted between deployments
- Either use a volume mount or include it in your Docker image
- Don't regenerate migrations on each deployment

### 2. Environment Variables

Always set these in your Docker environment:
```bash
FLASK_APP=app.py
DATABASE_URL=your_database_url
```

### 3. Production Workflow

1. **Development**: Create and test migrations locally
2. **Commit**: Add migration files to Git
3. **Build**: Include migrations in Docker image
4. **Deploy**: Startup script applies migrations automatically

### 4. Rollback Strategy

To rollback a migration:
```bash
# Inside container
flask db downgrade  # Go back one migration
flask db downgrade -2  # Go back two migrations
```

## Troubleshooting

### "No Git repository found"

This is expected in Docker. Use `docker_migrate_init.py` instead of the Git-based scripts.

### "Can't locate revision"

Your database references a migration that doesn't exist:
```bash
# Reset to current state
python docker_migrate_init.py
flask db stamp head
```

### Migration conflicts after deployment

If migrations were created in different environments:
```bash
# Merge migrations
flask db merge -m "Merge production and development"
flask db upgrade
```

## Best Practices

1. **Always test migrations** in a staging environment first
2. **Back up your database** before applying migrations in production
3. **Include migrations in your Docker image** for consistency
4. **Don't generate migrations in production** - only apply pre-tested ones
5. **Monitor the startup logs** to ensure migrations apply successfully

## Migration State in Different Scenarios

### Scenario 1: Fresh deployment, empty database
- Startup script runs `docker_migrate_init.py`
- Creates baseline migration
- Applies it to create all tables

### Scenario 2: Existing database, first Flask-Migrate setup
- Startup script runs `docker_migrate_init.py`
- Creates baseline migration matching current schema
- Stamps database as current (no changes)

### Scenario 3: Subsequent deployments with new migrations
- Startup script detects `migrations/` exists
- Runs `flask db upgrade` to apply new migrations

### Scenario 4: Container restart (no new code)
- Startup script detects `migrations/` exists
- Runs `flask db upgrade` (no-op if already current)

This approach ensures migrations work correctly in all Docker deployment scenarios!