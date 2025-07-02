"""
Data export utilities for TimeTrack application.
Handles exporting time entries and analytics data to various file formats (CSV, Excel).
"""

import io
import csv
import pandas as pd
from flask import Response, send_file
from datetime import datetime
from data_formatting import format_duration


def export_to_csv(data, filename):
    """Export data to CSV format."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}.csv'}
    )


def export_to_excel(data, filename):
    """Export data to Excel format with formatting."""
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='TimeTrack Data', index=False)
        
        # Auto-adjust columns' width
        worksheet = writer.sheets['TimeTrack Data']
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_width)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"{filename}.xlsx"
    )


def export_team_hours_to_csv(data, filename):
    """Export team hours data to CSV format."""
    if not data:
        return None
        
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}.csv'}
    )


def export_team_hours_to_excel(data, filename, team_name):
    """Export team hours data to Excel format with formatting."""
    if not data:
        return None
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=f'{team_name} Hours', index=False)
        
        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets[f'{team_name} Hours']
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1
        })
        
        # Auto-adjust columns' width and apply formatting
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_width)
            
            # Apply header formatting
            worksheet.write(0, i, col, header_format)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"{filename}.xlsx"
    )


def export_analytics_csv(entries, view_type, mode):
    """Export analytics data as CSV."""
    output = io.StringIO()
    
    if view_type == 'team':
        # Team summary CSV
        writer = csv.writer(output)
        writer.writerow(['Team Member', 'Total Hours', 'Total Entries'])
        
        # Group by user
        user_data = {}
        for entry in entries:
            if entry.departure_time and entry.duration:
                username = entry.user.username
                if username not in user_data:
                    user_data[username] = {'hours': 0, 'entries': 0}
                user_data[username]['hours'] += entry.duration / 3600
                user_data[username]['entries'] += 1
        
        for username, data in user_data.items():
            writer.writerow([username, f"{data['hours']:.2f}", data['entries']])
    else:
        # Detailed entries CSV
        writer = csv.writer(output)
        headers = ['Date', 'Arrival Time', 'Departure Time', 'Duration', 'Break Duration', 'Project Code', 'Project Name', 'Notes']
        if mode == 'team':
            headers.insert(1, 'User')
        writer.writerow(headers)
        
        for entry in entries:
            row = [
                entry.arrival_time.strftime('%Y-%m-%d'),
                entry.arrival_time.strftime('%H:%M:%S'),
                entry.departure_time.strftime('%H:%M:%S') if entry.departure_time else 'Active',
                format_duration(entry.duration) if entry.duration else 'In progress',
                format_duration(entry.total_break_duration),
                entry.project.code if entry.project else '',
                entry.project.name if entry.project else 'No Project',
                entry.notes or ''
            ]
            if mode == 'team':
                row.insert(1, entry.user.username)
            writer.writerow(row)
    
    output.seek(0)
    filename = f"analytics_{view_type}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


def export_analytics_excel(entries, view_type, mode):
    """Export analytics data as Excel."""
    try:
        output = io.BytesIO()
        
        if view_type == 'team':
            # Team summary Excel
            user_data = {}
            for entry in entries:
                if entry.departure_time and entry.duration:
                    username = entry.user.username
                    if username not in user_data:
                        user_data[username] = {'hours': 0, 'entries': 0}
                    user_data[username]['hours'] += entry.duration / 3600
                    user_data[username]['entries'] += 1
            
            df = pd.DataFrame([
                {
                    'Team Member': username,
                    'Total Hours': f"{data['hours']:.2f}",
                    'Total Entries': data['entries']
                }
                for username, data in user_data.items()
            ])
        else:
            # Detailed entries Excel
            data_list = []
            for entry in entries:
                row_data = {
                    'Date': entry.arrival_time.strftime('%Y-%m-%d'),
                    'Arrival Time': entry.arrival_time.strftime('%H:%M:%S'),
                    'Departure Time': entry.departure_time.strftime('%H:%M:%S') if entry.departure_time else 'Active',
                    'Duration': format_duration(entry.duration) if entry.duration else 'In progress',
                    'Break Duration': format_duration(entry.total_break_duration),
                    'Project Code': entry.project.code if entry.project else '',
                    'Project Name': entry.project.name if entry.project else 'No Project',
                    'Notes': entry.notes or ''
                }
                if mode == 'team':
                    row_data['User'] = entry.user.username
                data_list.append(row_data)
            
            df = pd.DataFrame(data_list)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Analytics Data', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Analytics Data']
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BD',
                'border': 1
            })
            
            # Write headers with formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        filename = f"analytics_{view_type}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        raise Exception(f"Error creating Excel export: {str(e)}")