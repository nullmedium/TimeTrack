-- Migration: Add Billing Fields to Projects and Time Entries
-- Description: Implements Phase 1 and 2 of billable/non-billable hours tracking

-- Add billing fields to the project table
ALTER TABLE project ADD COLUMN IF NOT EXISTS billing_type VARCHAR(20) DEFAULT 'NON_BILLABLE' NOT NULL;
ALTER TABLE project ADD COLUMN IF NOT EXISTS hourly_rate NUMERIC(10, 2);
ALTER TABLE project ADD COLUMN IF NOT EXISTS billing_notes TEXT;

-- Add billing override fields to time_entry table
ALTER TABLE time_entry ADD COLUMN IF NOT EXISTS is_billable BOOLEAN;
ALTER TABLE time_entry ADD COLUMN IF NOT EXISTS billing_rate NUMERIC(10, 2);
ALTER TABLE time_entry ADD COLUMN IF NOT EXISTS billing_amount NUMERIC(10, 2);

-- Add check constraint for billing_type values
ALTER TABLE project ADD CONSTRAINT check_billing_type 
    CHECK (billing_type IN ('NON_BILLABLE', 'HOURLY', 'FIXED_RATE'));

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_project_billing_type ON project(billing_type);
CREATE INDEX IF NOT EXISTS idx_time_entry_is_billable ON time_entry(is_billable);

-- Update existing projects to have default billing configuration
-- This ensures backward compatibility
UPDATE project 
SET billing_type = 'NON_BILLABLE' 
WHERE billing_type IS NULL;

-- Add comment to explain the is_billable field behavior
COMMENT ON COLUMN time_entry.is_billable IS 'NULL means inherit from project, TRUE/FALSE overrides project setting';
COMMENT ON COLUMN time_entry.billing_rate IS 'Override rate for this specific time entry';
COMMENT ON COLUMN time_entry.billing_amount IS 'Calculated billing amount (hours * rate)';

-- Add comments for project billing fields
COMMENT ON COLUMN project.billing_type IS 'Billing type: Non-Billable, Hourly, or Fixed Rate';
COMMENT ON COLUMN project.hourly_rate IS 'Default hourly rate for this project';
COMMENT ON COLUMN project.billing_notes IS 'Special billing instructions or notes';