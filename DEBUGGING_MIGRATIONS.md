# Debugging Migration Issues in Docker

## Quick Solutions

### Container Exits Immediately

Use one of these approaches:

1. **Debug Mode (Recommended)**
   ```bash
   docker-compose down
   DEBUG_MODE=true docker-compose up
   ```

2. **Skip Migrations Temporarily**
   ```bash
   docker-compose down
   SKIP_MIGRATIONS=true docker-compose up
   ```

3. **Use Debug Compose File**
   ```bash
   docker-compose -f docker-compose.debug.yml up
   docker exec -it timetrack_web_1 bash
   ```

## Debug Entrypoint

The `debug_entrypoint.sh` keeps the container running and provides diagnostic info:

```bash
# In docker-compose.yml, change:
command: ["./startup_postgres.sh"]
# To:
entrypoint: ["./debug_entrypoint.sh"]

# Then:
docker-compose up -d
docker exec -it <container_name> bash
```

## Safe Startup Script

`startup_postgres_safe.sh` has three modes:

1. **Normal Mode**: Exits on migration failure (default)
2. **Debug Mode**: Continues running even if migrations fail
   ```bash
   DEBUG_MODE=true docker-compose up
   ```
3. **Skip Mode**: Skips migrations entirely
   ```bash
   SKIP_MIGRATIONS=true docker-compose up
   ```

## Common Debugging Steps

### 1. Get Into the Container
```bash
# If container keeps exiting, use debug compose:
docker-compose -f docker-compose.debug.yml up -d web
docker exec -it timetrack_web_1 bash

# Or modify your docker-compose.yml:
# Add: stdin_open: true
# Add: tty: true
# Change: entrypoint: ["/bin/bash"]
```

### 2. Manual Migration Setup
```bash
# Inside container:
export FLASK_APP=app.py

# Check what's wrong
python diagnose_migrations.py

# Initialize migrations
python docker_migrate_init.py

# Fix revision issues
python fix_revision_mismatch.py
```

### 3. Database Connection Issues
```bash
# Test connection
python -c "from app import app, db; app.app_context().push(); db.engine.execute('SELECT 1')"

# Check environment
echo $DATABASE_URL
echo $POSTGRES_HOST
```

### 4. Reset Everything
```bash
# Inside container:
rm -rf migrations
python docker_migrate_init.py
flask db stamp head  # For existing DB
flask db upgrade     # For new DB
```

## Docker Compose Examples

### Development with Auto-Restart
```yaml
services:
  web:
    environment:
      - DEBUG_MODE=true
    restart: unless-stopped  # Auto-restart on failure
```

### Interactive Debugging
```yaml
services:
  web:
    entrypoint: ["/app/debug_entrypoint.sh"]
    stdin_open: true
    tty: true
```

### Skip Migrations for Testing
```yaml
services:
  web:
    environment:
      - SKIP_MIGRATIONS=true
```

## Environment Variables

- `DEBUG_MODE=true` - Continue running even if migrations fail
- `SKIP_MIGRATIONS=true` - Skip all migration steps
- `FLASK_APP=app.py` - Required for Flask-Migrate
- `DATABASE_URL` - PostgreSQL connection string

## Step-by-Step Troubleshooting

1. **Container won't start?**
   ```bash
   # Use debug compose
   docker-compose -f docker-compose.debug.yml up
   ```

2. **Migration fails?**
   ```bash
   # Get into container
   docker exec -it <container> bash
   
   # Run diagnostics
   python diagnose_migrations.py
   ```

3. **Revision mismatch?**
   ```bash
   # Quick fix
   ./quick_fix_revision.sh
   
   # Or manual fix
   flask db stamp <revision>
   ```

4. **Can't initialize migrations?**
   ```bash
   # Check database connection first
   python -c "from app import app; print(app.config['SQLALCHEMY_DATABASE_URI'])"
   
   # Then initialize
   python docker_migrate_init.py
   ```

## Tips

1. **Always use volumes** for migrations directory in development
2. **Check logs carefully** - the error is usually clear
3. **Don't run migrations in production containers** - include pre-tested migrations in image
4. **Use DEBUG_MODE** during development for easier troubleshooting
5. **Test locally first** before deploying to production

## Recovery Commands

If everything is broken:

```bash
# 1. Start with debug entrypoint
docker-compose -f docker-compose.debug.yml up -d web

# 2. Get into container
docker exec -it timetrack_web_1 bash

# 3. Reset migrations
rm -rf migrations
python docker_migrate_init.py

# 4. Mark as current (existing DB) or create tables (new DB)
flask db stamp head  # Existing
flask db upgrade     # New

# 5. Test the app
python app.py  # Run in debug mode

# 6. If working, update docker-compose.yml and restart normally
```