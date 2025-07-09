"""
Data Aggregator - Handles complex data queries and aggregations for reports.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case, extract

from models import TimeEntry, User, Project, Task, Team, Sprint, TaskStatus


class DataAggregator:
    """Aggregates and transforms data for report components."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_time_series_data(self, filters: Dict, chart_type: str = 'line') -> Dict:
        """Get time series data for charts."""
        query = self._build_base_query(filters, TimeEntry)
        
        # Group by date
        results = query.with_entities(
            func.date(TimeEntry.arrival_time).label('date'),
            func.sum(TimeEntry.duration).label('total_seconds'),
            func.count(TimeEntry.id).label('entry_count')
        ).group_by(
            func.date(TimeEntry.arrival_time)
        ).order_by(
            func.date(TimeEntry.arrival_time)
        ).all()
        
        # Fill in missing dates
        date_range = self._get_date_range(filters)
        all_dates = self._generate_date_series(date_range['start'], date_range['end'])
        
        data_map = {str(r.date): round(r.total_seconds / 3600, 2) for r in results}
        
        series_data = []
        for date_str in all_dates:
            series_data.append({
                'date': date_str,
                'hours': data_map.get(date_str, 0)
            })
        
        return {
            'labels': [d['date'] for d in series_data],
            'datasets': [{
                'label': 'Hours Worked',
                'data': [d['hours'] for d in series_data]
            }],
            'chart_type': chart_type,
            'total_hours': sum(d['hours'] for d in series_data),
            'avg_hours': round(sum(d['hours'] for d in series_data) / len(series_data), 2) if series_data else 0
        }
    
    def get_project_distribution(self, filters: Dict, chart_type: str = 'doughnut') -> Dict:
        """Get project distribution data."""
        query = self._build_base_query(filters, TimeEntry)
        
        results = query.join(Project, isouter=True).with_entities(
            case(
                [(Project.id.is_(None), 'No Project')],
                else_=Project.name
            ).label('project_name'),
            func.sum(TimeEntry.duration).label('total_seconds')
        ).group_by('project_name').all()
        
        data = []
        for r in results:
            hours = round(r.total_seconds / 3600, 2)
            if hours > 0:
                data.append({
                    'project': r.project_name,
                    'hours': hours
                })
        
        # Sort by hours descending
        data.sort(key=lambda x: x['hours'], reverse=True)
        
        return {
            'labels': [d['project'] for d in data],
            'datasets': [{
                'data': [d['hours'] for d in data],
                'backgroundColor': self._get_color_palette(len(data))
            }],
            'chart_type': chart_type,
            'total_projects': len(data),
            'total_hours': sum(d['hours'] for d in data)
        }
    
    def get_burndown_data(self, filters: Dict) -> Dict:
        """Get burndown chart data for projects."""
        project_id = filters.get('project_id')
        if not project_id or project_id == 'none':
            return {'error': 'Project ID required for burndown chart'}
        
        # Get project and its tasks
        project = self.db.query(Project).filter_by(id=project_id).first()
        if not project:
            return {'error': 'Project not found'}
        
        # Get all tasks for the project
        tasks = self.db.query(Task).filter_by(project_id=project_id).all()
        
        if not tasks:
            return {
                'labels': [],
                'datasets': [],
                'chart_type': 'line',
                'total_tasks': 0
            }
        
        # Determine date range
        date_range = self._get_date_range(filters)
        if not date_range.get('start') or not date_range.get('end'):
            # Use project dates or task dates
            start_date = project.start_date or min(t.created_at.date() for t in tasks)
            end_date = project.end_date or date.today()
        else:
            start_date = date_range['start']
            end_date = date_range['end']
        
        # Generate date series
        dates = self._generate_date_series(start_date, end_date)
        total_tasks = len(tasks)
        
        # Calculate ideal burndown
        total_days = len(dates)
        ideal_burndown = []
        for i in range(total_days):
            remaining = total_tasks - (total_tasks * i / (total_days - 1)) if total_days > 1 else 0
            ideal_burndown.append(max(0, round(remaining, 1)))
        
        # Calculate actual burndown
        actual_burndown = []
        for date_str in dates:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            remaining = sum(1 for task in tasks if 
                           task.status != TaskStatus.DONE or 
                           (task.completed_date and task.completed_date > current_date))
            
            actual_burndown.append(remaining)
        
        return {
            'labels': dates,
            'datasets': [
                {
                    'label': 'Remaining Tasks',
                    'data': actual_burndown,
                    'borderColor': '#FF5722',
                    'fill': False
                },
                {
                    'label': 'Ideal Burndown',
                    'data': ideal_burndown,
                    'borderColor': '#4CAF50',
                    'borderDash': [5, 5],
                    'fill': False
                }
            ],
            'chart_type': 'line',
            'total_tasks': total_tasks,
            'completed_tasks': total_tasks - (actual_burndown[-1] if actual_burndown else 0),
            'completion_rate': round(((total_tasks - actual_burndown[-1]) / total_tasks * 100) if total_tasks > 0 else 0, 1)
        }
    
    def get_team_hours_data(self, filters: Dict) -> Dict:
        """Get team member hours for bar chart."""
        query = self._build_base_query(filters, TimeEntry)
        
        results = query.join(User).with_entities(
            User.username,
            func.sum(TimeEntry.duration).label('total_seconds')
        ).group_by(User.username).all()
        
        data = []
        for r in results:
            hours = round(r.total_seconds / 3600, 2)
            if hours > 0:
                data.append({
                    'member': r.username,
                    'hours': hours
                })
        
        # Sort by hours descending
        data.sort(key=lambda x: x['hours'], reverse=True)
        
        return {
            'labels': [d['member'] for d in data],
            'datasets': [{
                'label': 'Hours Worked',
                'data': [d['hours'] for d in data],
                'backgroundColor': '#2196F3'
            }],
            'chart_type': 'bar',
            'total_members': len(data),
            'total_hours': sum(d['hours'] for d in data)
        }
    
    def get_workload_heatmap(self, filters: Dict) -> Dict:
        """Get workload distribution heatmap data."""
        query = self._build_base_query(filters, TimeEntry)
        
        # Get hourly distribution by day of week
        results = query.with_entities(
            extract('dow', TimeEntry.arrival_time).label('day_of_week'),
            extract('hour', TimeEntry.arrival_time).label('hour'),
            func.count(TimeEntry.id).label('entry_count'),
            func.sum(TimeEntry.duration).label('total_seconds')
        ).group_by('day_of_week', 'hour').all()
        
        # Build heatmap data
        heatmap_data = defaultdict(lambda: defaultdict(int))
        for r in results:
            day = int(r.day_of_week)
            hour = int(r.hour)
            hours_worked = r.total_seconds / 3600
            heatmap_data[day][hour] = round(hours_worked, 2)
        
        # Convert to chart format
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        hours = list(range(24))
        
        series_data = []
        for day_idx, day_name in enumerate(days):
            for hour in hours:
                value = heatmap_data[day_idx][hour]
                if value > 0:
                    series_data.append({
                        'x': hour,
                        'y': day_idx,
                        'value': value,
                        'day': day_name,
                        'hour': f'{hour:02d}:00'
                    })
        
        return {
            'data': series_data,
            'chart_type': 'heatmap',
            'x_labels': [f'{h:02d}:00' for h in hours],
            'y_labels': days,
            'max_value': max((d['value'] for d in series_data), default=0)
        }
    
    def get_task_status_data(self, filters: Dict) -> Dict:
        """Get task status distribution."""
        project_id = filters.get('project_id')
        
        query = self.db.query(Task)
        if project_id and project_id != 'none':
            query = query.filter_by(project_id=project_id)
        
        # Apply date filters if completed date exists
        date_range = self._get_date_range(filters)
        if date_range.get('start'):
            query = query.filter(or_(
                Task.created_at >= date_range['start'],
                Task.completed_date >= date_range['start']
            ))
        
        results = query.with_entities(
            Task.status,
            func.count(Task.id).label('count')
        ).group_by(Task.status).all()
        
        status_map = {
            TaskStatus.TODO: 'To Do',
            TaskStatus.IN_PROGRESS: 'In Progress',
            TaskStatus.DONE: 'Done',
            TaskStatus.BLOCKED: 'Blocked'
        }
        
        data = []
        for r in results:
            data.append({
                'status': status_map.get(r.status, str(r.status)),
                'count': r.count
            })
        
        return {
            'labels': [d['status'] for d in data],
            'datasets': [{
                'label': 'Tasks',
                'data': [d['count'] for d in data],
                'backgroundColor': ['#FF9800', '#2196F3', '#4CAF50', '#F44336']
            }],
            'chart_type': 'bar',
            'total_tasks': sum(d['count'] for d in data)
        }
    
    def get_daily_pattern_data(self, filters: Dict) -> Dict:
        """Get daily hours pattern for the week."""
        # Get last 7 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        
        filters['date_range'] = {
            'start': start_date,
            'end': end_date
        }
        
        query = self._build_base_query(filters, TimeEntry)
        
        results = query.with_entities(
            func.date(TimeEntry.arrival_time).label('date'),
            func.sum(TimeEntry.duration).label('total_seconds')
        ).group_by('date').order_by('date').all()
        
        # Build data for last 7 days
        data = []
        current = start_date
        result_map = {str(r.date): r.total_seconds / 3600 for r in results}
        
        while current <= end_date:
            data.append({
                'date': current.strftime('%a %m/%d'),
                'hours': round(result_map.get(str(current), 0), 2)
            })
            current += timedelta(days=1)
        
        return {
            'labels': [d['date'] for d in data],
            'datasets': [{
                'label': 'Hours',
                'data': [d['hours'] for d in data],
                'backgroundColor': '#4CAF50'
            }],
            'chart_type': 'bar',
            'total_hours': sum(d['hours'] for d in data),
            'avg_hours': round(sum(d['hours'] for d in data) / 7, 2)
        }
    
    def get_time_entries_table(self, filters: Dict, columns: List[str]) -> Dict:
        """Get time entries for table display."""
        query = self._build_base_query(filters, TimeEntry)
        
        # Eager load relationships
        query = query.options(
            joinedload(TimeEntry.user),
            joinedload(TimeEntry.project)
        )
        
        # Apply pagination
        page = filters.get('page', 1)
        per_page = filters.get('per_page', 50)
        
        total = query.count()
        entries = query.order_by(
            TimeEntry.arrival_time.desc()
        ).limit(per_page).offset((page - 1) * per_page).all()
        
        rows = []
        for entry in entries:
            row = {}
            if 'date' in columns:
                row['date'] = entry.arrival_time.strftime('%Y-%m-%d')
            if 'user' in columns:
                row['user'] = entry.user.username if entry.user else ''
            if 'project' in columns:
                row['project'] = entry.project.name if entry.project else 'No Project'
            if 'arrival' in columns:
                row['arrival'] = entry.arrival_time.strftime('%H:%M')
            if 'departure' in columns:
                row['departure'] = entry.departure_time.strftime('%H:%M') if entry.departure_time else 'Active'
            if 'duration' in columns:
                row['duration'] = self._format_duration(entry.duration)
            if 'notes' in columns:
                row['notes'] = entry.notes or ''
            
            rows.append(row)
        
        return {
            'columns': columns,
            'rows': rows,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def get_milestones_table(self, filters: Dict, columns: List[str]) -> Dict:
        """Get project milestones for table display."""
        project_id = filters.get('project_id')
        if not project_id:
            return {'columns': columns, 'rows': [], 'total': 0}
        
        # For now, we'll use sprints as milestones
        query = self.db.query(Sprint).filter_by(project_id=project_id)
        
        sprints = query.order_by(Sprint.start_date).all()
        
        rows = []
        for sprint in sprints:
            row = {}
            if 'milestone' in columns:
                row['milestone'] = sprint.name
            if 'status' in columns:
                row['status'] = 'Active' if sprint.is_active else 'Completed'
            if 'due_date' in columns:
                row['due_date'] = sprint.end_date.strftime('%Y-%m-%d') if sprint.end_date else ''
            if 'progress' in columns:
                # Calculate progress based on completed tasks
                total_tasks = len(sprint.tasks) if hasattr(sprint, 'tasks') else 0
                completed_tasks = sum(1 for t in sprint.tasks if t.status == TaskStatus.DONE) if hasattr(sprint, 'tasks') else 0
                row['progress'] = f'{completed_tasks}/{total_tasks}'
            
            rows.append(row)
        
        return {
            'columns': columns,
            'rows': rows,
            'total': len(rows)
        }
    
    def get_team_summary_table(self, filters: Dict, columns: List[str]) -> Dict:
        """Get team member summary for table display."""
        query = self._build_base_query(filters, TimeEntry)
        
        results = query.join(User).with_entities(
            User.username,
            User.email,
            func.sum(TimeEntry.duration).label('total_seconds'),
            func.count(func.distinct(TimeEntry.project_id)).label('project_count'),
            func.count(func.distinct(func.date(TimeEntry.arrival_time))).label('days_worked')
        ).group_by(User.id, User.username, User.email).all()
        
        rows = []
        for r in results:
            row = {}
            if 'member' in columns:
                row['member'] = r.username
            if 'email' in columns:
                row['email'] = r.email
            if 'hours' in columns:
                row['hours'] = round(r.total_seconds / 3600, 2)
            if 'projects' in columns:
                row['projects'] = r.project_count
            if 'days' in columns:
                row['days'] = r.days_worked
            if 'avg_hours' in columns:
                avg = (r.total_seconds / 3600 / r.days_worked) if r.days_worked > 0 else 0
                row['avg_hours'] = round(avg, 2)
            
            rows.append(row)
        
        # Sort by hours descending
        rows.sort(key=lambda x: x.get('hours', 0), reverse=True)
        
        return {
            'columns': columns,
            'rows': rows,
            'total': len(rows)
        }
    
    def get_project_summary_table(self, filters: Dict, columns: List[str]) -> Dict:
        """Get project summary for table display."""
        query = self._build_base_query(filters, TimeEntry)
        
        results = query.join(Project, isouter=True).with_entities(
            case(
                [(Project.id.is_(None), 'No Project')],
                else_=Project.name
            ).label('project_name'),
            Project.code,
            func.sum(TimeEntry.duration).label('total_seconds'),
            func.count(func.distinct(TimeEntry.user_id)).label('member_count'),
            func.min(TimeEntry.arrival_time).label('first_entry'),
            func.max(TimeEntry.arrival_time).label('last_entry')
        ).group_by(Project.id, Project.name, Project.code).all()
        
        rows = []
        for r in results:
            row = {}
            if 'project' in columns:
                row['project'] = r.project_name
            if 'code' in columns:
                row['code'] = r.code or ''
            if 'hours' in columns:
                row['hours'] = round(r.total_seconds / 3600, 2)
            if 'members' in columns:
                row['members'] = r.member_count
            if 'first_entry' in columns:
                row['first_entry'] = r.first_entry.strftime('%Y-%m-%d') if r.first_entry else ''
            if 'last_entry' in columns:
                row['last_entry'] = r.last_entry.strftime('%Y-%m-%d') if r.last_entry else ''
            if 'progress' in columns:
                # This would need actual progress calculation
                row['progress'] = 'N/A'
            
            rows.append(row)
        
        # Sort by hours descending
        rows.sort(key=lambda x: x.get('hours', 0), reverse=True)
        
        return {
            'columns': columns,
            'rows': rows,
            'total': len(rows)
        }
    
    def _build_base_query(self, filters: Dict, model):
        """Build base query with common filters."""
        query = self.db.query(model)
        
        # Date range filtering
        date_range = filters.get('date_range', {})
        if date_range.get('start'):
            if model == TimeEntry:
                query = query.filter(TimeEntry.arrival_time >= date_range['start'])
            elif model == Task:
                query = query.filter(Task.created_at >= date_range['start'])
                
        if date_range.get('end'):
            # Add one day to include the end date
            end_date = date_range['end']
            if isinstance(end_date, date):
                end_date = datetime.combine(end_date, datetime.max.time())
            else:
                end_date = end_date + timedelta(days=1)
                
            if model == TimeEntry:
                query = query.filter(TimeEntry.arrival_time < end_date)
            elif model == Task:
                query = query.filter(Task.created_at < end_date)
        
        # User/Team filtering
        if 'user_id' in filters:
            if model == TimeEntry:
                query = query.filter_by(user_id=filters['user_id'])
            elif model == Task:
                query = query.filter_by(assigned_to_id=filters['user_id'])
                
        if 'team_id' in filters and model == TimeEntry:
            team_users = self.db.query(User.id).filter_by(team_id=filters['team_id'])
            query = query.filter(TimeEntry.user_id.in_(team_users))
        
        # Project filtering
        if 'project_id' in filters:
            if filters['project_id'] == 'none':
                query = query.filter(model.project_id.is_(None))
            else:
                query = query.filter_by(project_id=filters['project_id'])
        
        # Only completed entries for time calculations
        if model == TimeEntry and filters.get('completed_only', True):
            query = query.filter(TimeEntry.departure_time.isnot(None))
        
        return query
    
    def _get_date_range(self, filters: Dict) -> Dict:
        """Extract and normalize date range from filters."""
        date_range = filters.get('date_range', {})
        
        # Convert string dates to date objects
        if isinstance(date_range.get('start'), str):
            date_range['start'] = datetime.strptime(date_range['start'], '%Y-%m-%d').date()
        if isinstance(date_range.get('end'), str):
            date_range['end'] = datetime.strptime(date_range['end'], '%Y-%m-%d').date()
        
        # Default to last 30 days if not specified
        if not date_range.get('end'):
            date_range['end'] = date.today()
        if not date_range.get('start'):
            date_range['start'] = date_range['end'] - timedelta(days=30)
            
        return date_range
    
    def _generate_date_series(self, start_date: date, end_date: date) -> List[str]:
        """Generate a series of dates between start and end."""
        dates = []
        current = start_date
        
        while current <= end_date:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
            
        return dates
    
    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in seconds to HH:MM:SS."""
        if not seconds:
            return '00:00:00'
            
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    
    def _get_color_palette(self, count: int) -> List[str]:
        """Get a color palette for charts."""
        colors = [
            '#4CAF50', '#2196F3', '#FF9800', '#E91E63',
            '#9C27B0', '#00BCD4', '#8BC34A', '#FFC107',
            '#795548', '#607D8B', '#F44336', '#3F51B5',
            '#009688', '#CDDC39', '#FF5722', '#673AB7'
        ]
        
        # Repeat colors if needed
        while len(colors) < count:
            colors.extend(colors)
            
        return colors[:count]