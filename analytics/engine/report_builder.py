"""
Report Builder Engine - Core module for creating and managing custom reports.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from models import ReportTemplate, SavedReport, ReportComponent, ReportShare, User, TimeEntry, Project, Task, Team
from analytics.engine.data_aggregator import DataAggregator


class ReportBuilder:
    """Main class for building and executing reports."""
    
    def __init__(self, db_session: Session, user: User):
        self.db = db_session
        self.user = user
        self.aggregator = DataAggregator(db_session)
        
    def create_report(self, name: str, template_id: Optional[int] = None, 
                     config: Optional[Dict] = None) -> SavedReport:
        """Create a new report from template or custom config."""
        report = SavedReport(
            user_id=self.user.id,
            name=name,
            template_id=template_id
        )
        
        if template_id:
            template = self.db.query(ReportTemplate).filter_by(id=template_id).first()
            if template:
                report.config = template.template_config
                report.description = f"Based on {template.name}"
        
        if config:
            report.config = config
            
        self.db.add(report)
        self.db.commit()
        return report
    
    def update_report(self, report_id: int, updates: Dict) -> SavedReport:
        """Update an existing report."""
        report = self.db.query(SavedReport).filter_by(
            id=report_id, user_id=self.user.id
        ).first()
        
        if not report:
            raise ValueError("Report not found or access denied")
        
        if 'name' in updates:
            report.name = updates['name']
        if 'description' in updates:
            report.description = updates['description']
        if 'config' in updates:
            report.config = updates['config']
        if 'filters' in updates:
            report.filters = updates['filters']
        if 'is_favorite' in updates:
            report.is_favorite = updates['is_favorite']
            
        self.db.commit()
        return report
    
    def execute_report(self, report_id: int, 
                      date_range: Optional[Dict] = None,
                      additional_filters: Optional[Dict] = None) -> Dict:
        """Execute a report and return the data."""
        report = self.db.query(SavedReport).filter_by(id=report_id).first()
        
        if not report:
            raise ValueError("Report not found")
            
        # Check access permissions
        if not self._can_access_report(report):
            raise ValueError("Access denied")
            
        # Update access stats
        report.update_access()
        self.db.commit()
        
        # Merge filters
        filters = report.filters.copy() if report.filters else {}
        if date_range:
            filters['date_range'] = date_range
        if additional_filters:
            filters.update(additional_filters)
            
        # Execute each component
        results = {
            'report_info': {
                'id': report.id,
                'name': report.name,
                'description': report.description,
                'executed_at': datetime.utcnow().isoformat()
            },
            'components': []
        }
        
        components = report.config.get('components', [])
        for component in components:
            component_data = self._execute_component(component, filters)
            results['components'].append(component_data)
            
        return results
    
    def _execute_component(self, component: Dict, filters: Dict) -> Dict:
        """Execute a single report component."""
        component_type = component.get('type')
        component_id = component.get('id')
        config = component.get('config', {})
        
        if component_type == 'metric':
            data = self._execute_metric(component_id, config, filters)
        elif component_type == 'chart':
            data = self._execute_chart(component_id, config, filters)
        elif component_type == 'table':
            data = self._execute_table(component_id, config, filters)
        elif component_type == 'text':
            data = self._execute_text(component_id, config, filters)
        else:
            data = {'error': f'Unknown component type: {component_type}'}
            
        return {
            'id': component_id,
            'type': component_type,
            'config': config,
            'data': data
        }
    
    def _execute_metric(self, metric_id: str, config: Dict, filters: Dict) -> Dict:
        """Execute a metric component."""
        metric_map = {
            'total_hours': self._get_total_hours,
            'days_worked': self._get_days_worked,
            'avg_daily_hours': self._get_avg_daily_hours,
            'completion_rate': self._get_completion_rate,
            'tasks_completed': self._get_tasks_completed,
            'team_size': self._get_team_size,
            'utilization_rate': self._get_utilization_rate
        }
        
        if metric_id in metric_map:
            value = metric_map[metric_id](filters)
            return {
                'value': value,
                'label': config.get('label', metric_id),
                'format': config.get('format', 'number')
            }
        
        return {'error': f'Unknown metric: {metric_id}'}
    
    def _execute_chart(self, chart_id: str, config: Dict, filters: Dict) -> Dict:
        """Execute a chart component."""
        chart_type = config.get('type', 'line')
        
        if chart_id == 'time_series':
            return self.aggregator.get_time_series_data(filters, chart_type)
        elif chart_id == 'project_dist':
            return self.aggregator.get_project_distribution(filters, chart_type)
        elif chart_id == 'burndown':
            return self.aggregator.get_burndown_data(filters)
        elif chart_id == 'member_hours':
            return self.aggregator.get_team_hours_data(filters)
        elif chart_id == 'workload_dist':
            return self.aggregator.get_workload_heatmap(filters)
        elif chart_id == 'task_status':
            return self.aggregator.get_task_status_data(filters)
        elif chart_id == 'daily_pattern':
            return self.aggregator.get_daily_pattern_data(filters)
        
        return {'error': f'Unknown chart: {chart_id}'}
    
    def _execute_table(self, table_id: str, config: Dict, filters: Dict) -> Dict:
        """Execute a table component."""
        columns = config.get('columns', [])
        
        if table_id == 'entries_table':
            return self.aggregator.get_time_entries_table(filters, columns)
        elif table_id == 'milestone_table':
            return self.aggregator.get_milestones_table(filters, columns)
        elif table_id == 'member_summary':
            return self.aggregator.get_team_summary_table(filters, columns)
        elif table_id == 'project_summary':
            return self.aggregator.get_project_summary_table(filters, columns)
        
        return {'error': f'Unknown table: {table_id}'}
    
    def _execute_text(self, text_id: str, config: Dict, filters: Dict) -> Dict:
        """Execute a text component."""
        template = config.get('template', '')
        variables = self._get_text_variables(filters)
        
        # Replace variables in template
        for key, value in variables.items():
            template = template.replace(f'{{{{{key}}}}}', str(value))
            
        return {
            'content': template,
            'title': config.get('title', ''),
            'editable': config.get('editable', False)
        }
    
    def _get_text_variables(self, filters: Dict) -> Dict:
        """Get variables for text templates."""
        date_range = filters.get('date_range', {})
        start_date = date_range.get('start', datetime.now().date() - timedelta(days=7))
        end_date = date_range.get('end', datetime.now().date())
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'user_name': self.user.username,
            'company_name': self.user.company.name if self.user.company else '',
            'current_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def _get_total_hours(self, filters: Dict) -> float:
        """Calculate total hours from time entries."""
        query = self._build_time_entry_query(filters)
        total_seconds = query.with_entities(func.sum(TimeEntry.duration)).scalar() or 0
        return round(total_seconds / 3600, 2)
    
    def _get_days_worked(self, filters: Dict) -> int:
        """Count unique days with time entries."""
        query = self._build_time_entry_query(filters)
        unique_dates = query.with_entities(
            func.date(TimeEntry.arrival_time)
        ).distinct().count()
        return unique_dates
    
    def _get_avg_daily_hours(self, filters: Dict) -> float:
        """Calculate average hours per day."""
        total_hours = self._get_total_hours(filters)
        days_worked = self._get_days_worked(filters)
        
        if days_worked == 0:
            return 0
        
        return round(total_hours / days_worked, 2)
    
    def _get_completion_rate(self, filters: Dict) -> float:
        """Calculate project/task completion rate."""
        project_id = filters.get('project_id')
        if not project_id:
            return 0
            
        total_tasks = self.db.query(Task).filter_by(project_id=project_id).count()
        completed_tasks = self.db.query(Task).filter_by(
            project_id=project_id,
            status='DONE'
        ).count()
        
        if total_tasks == 0:
            return 0
            
        return round((completed_tasks / total_tasks) * 100, 1)
    
    def _get_tasks_completed(self, filters: Dict) -> int:
        """Count completed tasks."""
        query = self.db.query(Task).filter_by(status='DONE')
        
        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
            
        date_range = filters.get('date_range', {})
        if 'start' in date_range:
            query = query.filter(Task.completed_date >= date_range['start'])
        if 'end' in date_range:
            query = query.filter(Task.completed_date <= date_range['end'])
            
        return query.count()
    
    def _get_team_size(self, filters: Dict) -> int:
        """Get team member count."""
        if self.user.team_id:
            return self.db.query(User).filter_by(
                team_id=self.user.team_id,
                is_active=True
            ).count()
        return 1
    
    def _get_utilization_rate(self, filters: Dict) -> float:
        """Calculate team utilization rate."""
        # Assuming 8 hours per day as standard
        total_possible_hours = self._get_days_worked(filters) * 8 * self._get_team_size(filters)
        actual_hours = self._get_total_hours(filters)
        
        if total_possible_hours == 0:
            return 0
            
        return round((actual_hours / total_possible_hours) * 100, 1)
    
    def _build_time_entry_query(self, filters: Dict):
        """Build base query for time entries with filters."""
        query = self.db.query(TimeEntry)
        
        # User/Team filtering
        if self.user.role not in ['ADMIN', 'SUPERVISOR', 'TEAM_LEADER']:
            query = query.filter_by(user_id=self.user.id)
        elif filters.get('team_mode') and self.user.team_id:
            team_users = self.db.query(User.id).filter_by(team_id=self.user.team_id)
            query = query.filter(TimeEntry.user_id.in_(team_users))
        
        # Date range filtering
        date_range = filters.get('date_range', {})
        if 'start' in date_range:
            query = query.filter(TimeEntry.arrival_time >= date_range['start'])
        if 'end' in date_range:
            query = query.filter(TimeEntry.arrival_time <= date_range['end'])
            
        # Project filtering
        if 'project_id' in filters:
            if filters['project_id'] == 'none':
                query = query.filter(TimeEntry.project_id.is_(None))
            else:
                query = query.filter_by(project_id=filters['project_id'])
                
        # Only completed entries for calculations
        query = query.filter(TimeEntry.departure_time.isnot(None))
        
        return query
    
    def _can_access_report(self, report: SavedReport) -> bool:
        """Check if user can access a report."""
        # Owner always has access
        if report.user_id == self.user.id:
            return True
            
        # Check shares
        for share in report.shares:
            if share.is_expired():
                continue
                
            if share.shared_with_user_id == self.user.id:
                return True
                
            if share.shared_with_team_id == self.user.team_id:
                return True
                
        return False
    
    def get_available_templates(self) -> List[ReportTemplate]:
        """Get templates available to the user."""
        query = self.db.query(ReportTemplate).filter(
            or_(
                ReportTemplate.is_public == True,
                ReportTemplate.company_id == self.user.company_id,
                ReportTemplate.created_by == self.user.id
            )
        )
        
        return query.order_by(
            ReportTemplate.is_system.desc(),
            ReportTemplate.category,
            ReportTemplate.name
        ).all()
    
    def get_user_reports(self, include_shared: bool = True) -> List[SavedReport]:
        """Get all reports accessible to the user."""
        # User's own reports
        reports = self.db.query(SavedReport).filter_by(
            user_id=self.user.id
        ).all()
        
        if include_shared:
            # Add shared reports
            filters = [ReportShare.shared_with_user_id == self.user.id]
            
            # Only add team filter if user has a team
            if self.user.team_id is not None:
                filters.append(ReportShare.shared_with_team_id == self.user.team_id)
            
            shared_reports = self.db.query(SavedReport).join(
                ReportShare
            ).filter(
                or_(*filters)
            ).all()
            
            # Merge and deduplicate
            report_ids = {r.id for r in reports}
            for report in shared_reports:
                if report.id not in report_ids:
                    reports.append(report)
                    
        return sorted(reports, key=lambda r: r.last_accessed or r.created_at, reverse=True)