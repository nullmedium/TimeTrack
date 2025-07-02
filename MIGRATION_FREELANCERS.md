# Freelancer Migration Guide

This document explains the database migration for freelancer support in TimeTrack.

## Overview

The freelancer migration adds support for independent users who can register without a company token. It introduces:

1. **Account Types**: Users can be either "Company User" or "Freelancer"
2. **Personal Companies**: Freelancers automatically get their own company workspace
3. **Business Names**: Optional field for freelancers to specify their business name

## Database Changes

### User Table Changes
- `account_type` VARCHAR(20) DEFAULT 'COMPANY_USER' - Type of account
- `business_name` VARCHAR(100) - Optional business name for freelancers  
- `company_id` INTEGER - Foreign key to company table (for multi-tenancy)

### Company Table Changes
- `is_personal` BOOLEAN DEFAULT 0 - Marks companies auto-created for freelancers

## Migration Options

### Option 1: Automatic Migration (Recommended)
The main migration script (`migrate_db.py`) now includes freelancer support:

```bash
python migrate_db.py
```

This will:
- Add new columns to existing tables
- Create company table if it doesn't exist
- Set default values for existing users

### Option 2: Dedicated Freelancer Migration
Use the dedicated freelancer migration script:

```bash
python migrate_freelancers.py
```

### Option 3: Manual SQL Migration
If you prefer manual control:

```sql
-- Add columns to user table
ALTER TABLE user ADD COLUMN account_type VARCHAR(20) DEFAULT 'COMPANY_USER';
ALTER TABLE user ADD COLUMN business_name VARCHAR(100);
ALTER TABLE user ADD COLUMN company_id INTEGER;

-- Create company table (if it doesn't exist)
CREATE TABLE company (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_personal BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    max_users INTEGER DEFAULT 100
);

-- Or add column to existing company table
ALTER TABLE company ADD COLUMN is_personal BOOLEAN DEFAULT 0;

-- Update existing users
UPDATE user SET account_type = 'COMPANY_USER' WHERE account_type IS NULL;
```

## Post-Migration Steps

### For Existing Installations
1. **Create Default Company**: If you have existing users without a company, create one:
   ```python
   # In Python/Flask shell
   from models import db, Company, User
   
   # Create default company
   company = Company(
       name="Default Company", 
       slug="default-company",
       description="Default company for existing users"
   )
   db.session.add(company)
   db.session.flush()
   
   # Assign existing users to default company
   User.query.filter_by(company_id=None).update({'company_id': company.id})
   db.session.commit()
   ```

2. **Verify Migration**: Check that all users have a company_id:
   ```sql
   SELECT COUNT(*) FROM user WHERE company_id IS NULL;
   -- Should return 0
   ```

### Testing Freelancer Registration
1. Visit `/register/freelancer`
2. Register a new freelancer account
3. Verify the personal company was created
4. Test login and time tracking functionality

## New Features Available

### Freelancer Registration
- **URL**: `/register/freelancer`  
- **Features**:
  - No company token required
  - Auto-creates personal workspace
  - Optional business name field
  - Immediate account activation

### Registration Options
- **Company Registration**: `/register` (existing)
- **Freelancer Registration**: `/register/freelancer` (new)
- **Login Page**: Shows both registration options

### User Experience
- Freelancers get admin privileges in their personal company
- Can create projects and track time immediately
- Personal workspace is limited to 1 user by default
- Can optionally expand to hire employees later

## Troubleshooting

### Common Issues

**Migration fails with "column already exists"**
- This is normal if you've run the migration before
- The migration script checks for existing columns

**Users missing company_id after migration**
- Run the post-migration steps above to assign a default company

**Freelancer registration fails**
- Check that the AccountType enum is imported correctly
- Verify database migration completed successfully

### Rollback (Limited)
SQLite doesn't support dropping columns, so rollback is limited:

```bash
python migrate_freelancers.py rollback
```

For full rollback, you would need to:
1. Export user data
2. Recreate tables without freelancer columns  
3. Re-import data

## Verification Commands

```bash
# Verify migration applied
python migrate_freelancers.py verify

# Check table structure
sqlite3 timetrack.db ".schema user"
sqlite3 timetrack.db ".schema company"

# Check data
sqlite3 timetrack.db "SELECT account_type, COUNT(*) FROM user GROUP BY account_type;"
```

## Security Considerations

- Freelancers get unique usernames/emails globally (not per-company)
- Personal companies are limited to 1 user by default
- Freelancers have admin privileges only in their personal workspace
- Multi-tenant isolation is maintained

## Future Enhancements

- Allow freelancers to upgrade to team accounts
- Billing integration for freelancer vs company accounts
- Advanced freelancer-specific features
- Integration with invoicing systems