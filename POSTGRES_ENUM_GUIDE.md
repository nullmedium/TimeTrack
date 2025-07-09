# PostgreSQL Enums with Flask-Migrate

## The Problem

PostgreSQL enums are **immutable** in many ways:
- Can't remove values
- Can't rename values  
- Can't change order (in older PostgreSQL versions)
- Flask-Migrate often doesn't detect enum changes

Your specific issue: The model has `TODO` but the database might have `To Do` or vice versa.

## Best Practices

### 1. Always Use UPPERCASE for Enum Values

```python
class TaskStatus(enum.Enum):
    TODO = "TODO"        # Good
    IN_PROGRESS = "IN_PROGRESS"  # Good
    # To Do = "To Do"    # Bad - spaces cause issues
```

### 2. Handle Enum Changes Manually

Flask-Migrate won't automatically handle enum changes. You must:

```python
# In your migration file's upgrade() function:
def upgrade():
    # Add new enum value
    op.execute("ALTER TYPE taskstatus ADD VALUE 'NEW_STATUS'")
    
    # Note: You CANNOT remove enum values in PostgreSQL!
```

### 3. Check Enum State Before Migrations

```bash
# Run this to see current state
python fix_postgres_enums.py

# Or manually check in psql:
\dT+ taskstatus
```

## Fixing Current Enum Issues

### Option 1: Quick Fix (Add Missing Values)

```sql
-- If model expects 'TODO' but DB has 'To Do'
ALTER TYPE taskstatus ADD VALUE 'TODO';

-- If model expects 'IN_PROGRESS' but DB has 'In Progress'  
ALTER TYPE taskstatus ADD VALUE 'IN_PROGRESS';
```

### Option 2: Create Migration

```bash
# Generate empty migration
flask db revision -m "Fix enum values"

# Edit migrations/versions/xxx_fix_enum_values.py
```

Add to upgrade():
```python
def upgrade():
    # Add missing enum values
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'TODO'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'DONE'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")
```

### Option 3: Data Migration (Complex)

If you need to change existing data from old to new values:

```python
def upgrade():
    # Add new value
    op.execute("ALTER TYPE taskstatus ADD VALUE 'TODO'")
    
    # Update existing data
    op.execute("UPDATE task SET status = 'TODO' WHERE status = 'To Do'")
    
    # Note: Can't remove 'To Do' - it stays forever!
```

## Enum Strategy Going Forward

### 1. Use String Columns Instead

Consider replacing enums with string columns + check constraints:

```python
# Instead of enum
status = db.Column(db.Enum(TaskStatus), default=TaskStatus.TODO)

# Use string with constraint
status = db.Column(db.String(20), default='TODO')
__table_args__ = (
    db.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE')"),
)
```

### 2. Create Enum Tables

Use a separate table for statuses:

```python
class TaskStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    
class Task(db.Model):
    status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'))
```

### 3. If Keeping Enums, Document Them

```python
class TaskStatus(enum.Enum):
    """
    Task status enum values.
    WARNING: These are PostgreSQL enums. 
    - NEVER change existing values
    - ONLY add new values at the end
    - To deprecate, mark in comments but don't remove
    """
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ARCHIVED = "ARCHIVED"
    # DEPRECATED - DO NOT USE
    # OLD_STATUS = "OLD_STATUS"  # Deprecated 2024-01-01
```

## Debugging Enum Issues

```bash
# 1. Check what's in the database
psql $DATABASE_URL -c "SELECT enum_range(NULL::taskstatus)"

# 2. Check what's in the model
python -c "from models import TaskStatus; print([e.value for e in TaskStatus])"

# 3. Run diagnostic
python fix_postgres_enums.py
```

## Emergency Fixes

If completely stuck:

```sql
-- Nuclear option: Drop and recreate
-- WARNING: This will fail if column is in use!

-- 1. Change column to text temporarily
ALTER TABLE task ALTER COLUMN status TYPE TEXT;

-- 2. Drop the enum
DROP TYPE taskstatus;

-- 3. Recreate with correct values
CREATE TYPE taskstatus AS ENUM ('TODO', 'IN_PROGRESS', 'DONE', 'ARCHIVED');

-- 4. Change column back
ALTER TABLE task ALTER COLUMN status TYPE taskstatus USING status::taskstatus;
```

## Prevention

1. **Always test enum migrations** on a copy of production data
2. **Keep enum values simple** - no spaces, all uppercase
3. **Document all enum values** in the model
4. **Consider alternatives** to enums for frequently changing values
5. **Add CHECK constraints** in addition to enums for validation

Remember: PostgreSQL enums are powerful but inflexible. Choose wisely!