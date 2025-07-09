-- Quick fix for enum value mismatches
-- Run this directly in PostgreSQL to fix the immediate issue

-- TaskStatus: Add enum NAMES as valid values
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'TODO';
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS';
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'IN_REVIEW';
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'DONE';
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'CANCELLED';
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ARCHIVED';

-- TaskPriority: Add enum NAMES as valid values
ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'LOW';
ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'MEDIUM';
ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'HIGH';
ALTER TYPE taskpriority ADD VALUE IF NOT EXISTS 'URGENT';

-- Role: Add enum NAMES as valid values (if used as enum)
-- ALTER TYPE role ADD VALUE IF NOT EXISTS 'TEAM_MEMBER';
-- ALTER TYPE role ADD VALUE IF NOT EXISTS 'TEAM_LEADER';
-- ALTER TYPE role ADD VALUE IF NOT EXISTS 'SUPERVISOR';
-- ALTER TYPE role ADD VALUE IF NOT EXISTS 'ADMIN';
-- ALTER TYPE role ADD VALUE IF NOT EXISTS 'SYSTEM_ADMIN';

-- To check what values are in each enum:
-- SELECT enum_range(NULL::taskstatus);
-- SELECT enum_range(NULL::taskpriority);