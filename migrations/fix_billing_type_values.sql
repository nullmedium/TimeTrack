-- Fix billing type values to use enum names instead of display values
-- First, drop the constraint
ALTER TABLE project DROP CONSTRAINT IF EXISTS check_billing_type;

-- Update any existing values to enum names
UPDATE project SET billing_type = 'NON_BILLABLE' WHERE billing_type = 'Non-Billable';
UPDATE project SET billing_type = 'HOURLY' WHERE billing_type = 'Hourly';
UPDATE project SET billing_type = 'FIXED_RATE' WHERE billing_type = 'Fixed Rate';

-- Re-add the constraint with correct values
ALTER TABLE project ADD CONSTRAINT check_billing_type 
    CHECK (billing_type IN ('NON_BILLABLE', 'HOURLY', 'FIXED_RATE'));