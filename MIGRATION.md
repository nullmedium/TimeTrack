# TimeTrack Database Migration Guide

This guide explains how to migrate your TimeTrack application from SQLite to PostgreSQL using Docker.

## Overview

TimeTrack now supports both SQLite and PostgreSQL databases. The migration process automatically converts your existing SQLite database to PostgreSQL while preserving all your data.

## Prerequisites

- Docker and Docker Compose installed
- Existing TimeTrack SQLite database
- Basic understanding of command line operations

## Quick Start (Automatic Migration)

1. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

The migration will happen automatically when you first start the application with PostgreSQL configured.

## Manual Migration Process

If you prefer to control the migration process manually:

1. **Prepare your environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your database credentials
   ```

2. **Start PostgreSQL and pgAdmin:**
   ```bash
   docker-compose up -d postgres pgadmin
   ```

3. **Run the migration script:**
   ```bash
   ./scripts/migrate.sh
   ```

4. **Start the application:**
   ```bash
   docker-compose up -d timetrack
   ```

## Configuration

### Environment Variables (.env)

```env
# Database Configuration
POSTGRES_DB=timetrack
POSTGRES_USER=timetrack
POSTGRES_PASSWORD=timetrack_password
POSTGRES_PORT=5432

# pgAdmin Configuration
PGADMIN_EMAIL=admin@timetrack.com
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050

# TimeTrack App Configuration
TIMETRACK_PORT=5000
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://timetrack:timetrack_password@postgres:5432/timetrack

# Mail Configuration
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=TimeTrack <noreply@timetrack.com>
```

### SQLite Path

By default, the migration looks for your SQLite database at `/data/timetrack.db`. If your database is located elsewhere, set the `SQLITE_PATH` environment variable:

```env
SQLITE_PATH=/path/to/your/timetrack.db
```

## Migration Process Details

The migration process includes:

1. **Database Connection**: Connects to both SQLite and PostgreSQL
2. **Backup Creation**: Creates a backup of existing PostgreSQL data (if any)
3. **Schema Creation**: Creates PostgreSQL tables using SQLAlchemy models
4. **Data Migration**: Transfers all data from SQLite to PostgreSQL
5. **Sequence Updates**: Updates PostgreSQL auto-increment sequences
6. **Verification**: Verifies that all data was migrated correctly

### Tables Migrated

- Companies and multi-tenancy data
- Users and authentication information
- Teams and project assignments
- Projects and categories
- Tasks and subtasks
- Time entries and work logs
- Work configurations and user preferences
- System settings

## Post-Migration

After successful migration:

1. **SQLite Database**: Renamed to `.migrated` to indicate completion
2. **Backup Files**: Created with timestamp for rollback if needed
3. **Application**: Automatically uses PostgreSQL for all operations
4. **Verification**: Check `migration.log` for detailed migration results

## Accessing pgAdmin

After starting the services, you can access pgAdmin at:
- URL: http://localhost:5050
- Email: admin@timetrack.com (or your configured email)
- Password: admin (or your configured password)

**Server Connection in pgAdmin:**
- Host: postgres
- Port: 5432
- Database: timetrack
- Username: timetrack
- Password: timetrack_password

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   - Ensure PostgreSQL container is running: `docker-compose ps postgres`
   - Check connection settings in .env file

2. **SQLite Database Not Found**
   - Verify the SQLite database path
   - Ensure the database file is accessible from the container

3. **Migration Fails**
   - Check `migration.log` for detailed error messages
   - Verify PostgreSQL has sufficient permissions
   - Ensure no data conflicts exist

4. **Data Verification Failed**
   - Compare row counts between SQLite and PostgreSQL
   - Check for foreign key constraint violations
   - Review migration.log for specific table issues

### Manual Recovery

If migration fails, you can:

1. **Restore from backup:**
   ```bash
   # Restore PostgreSQL from backup
   docker-compose exec postgres psql -U timetrack -d timetrack < postgres_backup_TIMESTAMP.sql
   ```

2. **Revert to SQLite:**
   ```bash
   # Rename migrated database back
   mv /data/timetrack.db.migrated /data/timetrack.db
   # Update .env to use SQLite
   DATABASE_URL=sqlite:////data/timetrack.db
   ```

## Performance Considerations

- Migration time depends on database size
- Large databases may take several minutes
- Migration runs in batches to optimize memory usage
- All operations are logged for monitoring

## Security Notes

- Change default passwords before production use
- Use strong, unique passwords for database access
- Ensure .env file is not committed to version control
- Regularly backup your PostgreSQL database

## Support

For issues or questions about the migration process:
1. Check the migration.log file for detailed error messages
2. Review this documentation for common solutions
3. Ensure all prerequisites are met
4. Verify environment configuration