-- Migration: Add Advanced Report Engine Tables
-- Description: Creates tables for report templates, saved reports, and report components

-- Report Templates Table
CREATE TABLE IF NOT EXISTS report_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) DEFAULT 'custom',
    template_config JSONB NOT NULL DEFAULT '{}',
    thumbnail TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES company(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Saved Reports Table
CREATE TABLE IF NOT EXISTS saved_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES report_templates(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    filters JSONB DEFAULT '{}',
    is_favorite BOOLEAN DEFAULT FALSE,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Report Components Table (for modular report building)
CREATE TABLE IF NOT EXISTS report_components (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'chart', 'table', 'metric', 'text'
    component_config JSONB NOT NULL DEFAULT '{}',
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Report Sharing Table
CREATE TABLE IF NOT EXISTS report_shares (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES saved_reports(id) ON DELETE CASCADE,
    shared_with_user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    shared_with_team_id INTEGER REFERENCES team(id) ON DELETE CASCADE,
    permission VARCHAR(20) DEFAULT 'view', -- 'view', 'edit'
    shared_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_share_target CHECK (
        (shared_with_user_id IS NOT NULL AND shared_with_team_id IS NULL) OR
        (shared_with_user_id IS NULL AND shared_with_team_id IS NOT NULL)
    )
);

-- Report Export History
CREATE TABLE IF NOT EXISTS report_export_history (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES saved_reports(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    export_format VARCHAR(20) NOT NULL, -- 'pdf', 'excel', 'csv', 'png'
    file_size INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_report_templates_company ON report_templates(company_id);
CREATE INDEX idx_report_templates_created_by ON report_templates(created_by);
CREATE INDEX idx_saved_reports_user ON saved_reports(user_id);
CREATE INDEX idx_saved_reports_template ON saved_reports(template_id);
CREATE INDEX idx_saved_reports_favorite ON saved_reports(user_id, is_favorite);
CREATE INDEX idx_report_shares_report ON report_shares(report_id);
CREATE INDEX idx_report_shares_user ON report_shares(shared_with_user_id);
CREATE INDEX idx_report_shares_team ON report_shares(shared_with_team_id);

-- Insert default system report templates
INSERT INTO report_templates (name, description, category, template_config, is_system, is_public) VALUES
('Time Summary Report', 'Overview of time tracked with charts and statistics', 'time_tracking', 
 '{"components": [
    {"type": "metric", "id": "total_hours", "config": {"label": "Total Hours", "format": "hours"}},
    {"type": "metric", "id": "days_worked", "config": {"label": "Days Worked", "format": "number"}},
    {"type": "metric", "id": "avg_daily_hours", "config": {"label": "Avg Hours/Day", "format": "hours"}},
    {"type": "chart", "id": "time_series", "config": {"type": "line", "title": "Daily Hours"}},
    {"type": "chart", "id": "project_dist", "config": {"type": "doughnut", "title": "Project Distribution"}},
    {"type": "table", "id": "entries_table", "config": {"columns": ["date", "project", "duration", "notes"]}}
  ]}', 
 TRUE, TRUE),

('Project Progress Report', 'Track project completion and burndown', 'projects',
 '{"components": [
    {"type": "metric", "id": "completion_rate", "config": {"label": "Completion", "format": "percentage"}},
    {"type": "metric", "id": "tasks_completed", "config": {"label": "Tasks Done", "format": "number"}},
    {"type": "metric", "id": "hours_logged", "config": {"label": "Hours Logged", "format": "hours"}},
    {"type": "chart", "id": "burndown", "config": {"type": "burndown", "title": "Project Burndown"}},
    {"type": "chart", "id": "task_status", "config": {"type": "bar", "title": "Task Status"}},
    {"type": "table", "id": "milestone_table", "config": {"columns": ["milestone", "status", "due_date"]}}
  ]}',
 TRUE, TRUE),

('Team Performance Report', 'Analyze team productivity and workload', 'team',
 '{"components": [
    {"type": "metric", "id": "team_size", "config": {"label": "Team Members", "format": "number"}},
    {"type": "metric", "id": "total_team_hours", "config": {"label": "Total Hours", "format": "hours"}},
    {"type": "metric", "id": "utilization_rate", "config": {"label": "Utilization", "format": "percentage"}},
    {"type": "chart", "id": "member_hours", "config": {"type": "bar", "title": "Hours by Member"}},
    {"type": "chart", "id": "workload_dist", "config": {"type": "heatmap", "title": "Workload Distribution"}},
    {"type": "table", "id": "member_summary", "config": {"columns": ["member", "hours", "projects", "tasks"]}}
  ]}',
 TRUE, TRUE),

('Weekly Status Report', 'Weekly summary of activities and progress', 'status',
 '{"components": [
    {"type": "text", "id": "week_header", "config": {"template": "Week of {{start_date}} - {{end_date}}"}},
    {"type": "metric", "id": "weekly_hours", "config": {"label": "Hours This Week", "format": "hours"}},
    {"type": "metric", "id": "tasks_completed", "config": {"label": "Tasks Completed", "format": "number"}},
    {"type": "chart", "id": "daily_pattern", "config": {"type": "bar", "title": "Daily Hours"}},
    {"type": "table", "id": "project_summary", "config": {"columns": ["project", "hours", "progress"]}},
    {"type": "text", "id": "notes_section", "config": {"title": "Weekly Notes", "editable": true}}
  ]}',
 TRUE, TRUE);

-- Insert default report components
INSERT INTO report_components (name, type, component_config, is_system) VALUES
('Total Hours Metric', 'metric', '{"data_source": "time_entries", "aggregation": "sum", "field": "duration"}', TRUE),
('Project Distribution Chart', 'chart', '{"chart_type": "doughnut", "data_source": "time_entries", "group_by": "project_id"}', TRUE),
('Time Series Chart', 'chart', '{"chart_type": "line", "data_source": "time_entries", "group_by": "date", "aggregation": "sum"}', TRUE),
('Basic Table', 'table', '{"data_source": "time_entries", "default_columns": ["date", "project", "duration"]}', TRUE),
('Text Block', 'text', '{"rich_text": true, "variables_supported": true}', TRUE);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_report_templates_updated_at BEFORE UPDATE ON report_templates
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saved_reports_updated_at BEFORE UPDATE ON saved_reports
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();