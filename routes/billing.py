"""
Billing and financial reporting routes
"""

from flask import Blueprint, render_template, request, g, jsonify, send_file, make_response
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_, case
from models import db, TimeEntry, Project, User, CompanySettings
from models.enums import BillingType
from routes.auth import role_required, company_required, Role
from utils.currency import get_currency_symbol, format_money
import calendar
import io
import csv
import xlsxwriter

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')


@billing_bp.route('/report')
@role_required(Role.SUPERVISOR)
@company_required
def billing_report():
    """Main billing report view"""
    # Get date range from request or default to current month
    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    
    # Calculate date range
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # Get filter parameters
    project_id = request.args.get('project_id', type=int)
    user_id = request.args.get('user_id', type=int)
    
    # Get company settings for currency
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    currency_symbol = get_currency_symbol(currency)
    
    # Get billing data
    billing_data = get_billing_data(
        company_id=g.user.company_id,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
        user_id=user_id
    )
    
    # Check if export is requested
    if request.args.get('export') == 'true':
        format_type = request.args.get('format', 'excel')
        if format_type == 'excel':
            return export_billing_excel(billing_data, currency, currency_symbol, year, month)
        elif format_type == 'csv':
            return export_billing_csv(billing_data, currency, currency_symbol, year, month)
    
    # Get available projects and users for filters
    projects = Project.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).filter(
        Project.billing_type != BillingType.NON_BILLABLE
    ).order_by(Project.name).all()
    
    users = User.query.filter_by(
        company_id=g.user.company_id,
        is_blocked=False
    ).order_by(User.username).all()
    
    # Generate month options for date selector
    months = []
    current_date = datetime.now()
    for i in range(12):
        month_date = current_date - timedelta(days=30 * i)
        months.append({
            'year': month_date.year,
            'month': month_date.month,
            'label': month_date.strftime('%B %Y')
        })
    
    return render_template('billing_report.html',
                         title='Billing Report',
                         billing_data=billing_data,
                         projects=projects,
                         users=users,
                         months=months,
                         selected_year=year,
                         selected_month=month,
                         selected_project_id=project_id,
                         selected_user_id=user_id,
                         currency=currency,
                         currency_symbol=currency_symbol,
                         format_money=format_money)


def get_billing_data(company_id, start_date, end_date, project_id=None, user_id=None):
    """Get aggregated billing data for the specified period"""
    
    # Base query for time entries
    query = db.session.query(
        TimeEntry,
        Project,
        User
    ).join(
        Project, TimeEntry.project_id == Project.id
    ).join(
        User, TimeEntry.user_id == User.id
    ).filter(
        Project.company_id == company_id,
        TimeEntry.arrival_time >= start_date,
        TimeEntry.arrival_time <= datetime.combine(end_date, datetime.max.time()),
        TimeEntry.departure_time.isnot(None)  # Only completed entries
    )
    
    # Apply filters
    if project_id:
        query = query.filter(Project.id == project_id)
    
    if user_id:
        query = query.filter(User.id == user_id)
    
    # Get all entries
    entries = query.all()
    
    # Process and aggregate data
    summary = {
        'total_hours': 0,
        'billable_hours': 0,
        'non_billable_hours': 0,
        'total_amount': 0,
        'by_project': {},
        'by_user': {},
        'by_date': {},
        'entries': []
    }
    
    for entry, project, user in entries:
        hours = entry.duration / 3600.0 if entry.duration else 0
        
        # Determine if billable
        is_billable = entry.effective_is_billable
        billing_rate = entry.effective_billing_rate
        amount = entry.calculate_billing_amount()
        
        # Update totals
        summary['total_hours'] += hours
        if is_billable:
            summary['billable_hours'] += hours
            summary['total_amount'] += amount
        else:
            summary['non_billable_hours'] += hours
        
        # Aggregate by project
        if project.id not in summary['by_project']:
            summary['by_project'][project.id] = {
                'project': project,
                'total_hours': 0,
                'billable_hours': 0,
                'non_billable_hours': 0,
                'total_amount': 0,
                'users': set()
            }
        
        proj_data = summary['by_project'][project.id]
        proj_data['total_hours'] += hours
        proj_data['users'].add(user.username)
        
        if is_billable:
            proj_data['billable_hours'] += hours
            proj_data['total_amount'] += amount
        else:
            proj_data['non_billable_hours'] += hours
        
        # Aggregate by user
        if user.id not in summary['by_user']:
            summary['by_user'][user.id] = {
                'user': user,
                'total_hours': 0,
                'billable_hours': 0,
                'non_billable_hours': 0,
                'total_amount': 0,
                'projects': set()
            }
        
        user_data = summary['by_user'][user.id]
        user_data['total_hours'] += hours
        user_data['projects'].add(project.name)
        
        if is_billable:
            user_data['billable_hours'] += hours
            user_data['total_amount'] += amount
        else:
            user_data['non_billable_hours'] += hours
        
        # Aggregate by date
        entry_date = entry.arrival_time.date()
        date_key = entry_date.strftime('%Y-%m-%d')
        
        if date_key not in summary['by_date']:
            summary['by_date'][date_key] = {
                'date': entry_date,
                'total_hours': 0,
                'billable_hours': 0,
                'total_amount': 0
            }
        
        date_data = summary['by_date'][date_key]
        date_data['total_hours'] += hours
        
        if is_billable:
            date_data['billable_hours'] += hours
            date_data['total_amount'] += amount
        
        # Add to entries list (for detailed view)
        summary['entries'].append({
            'date': entry_date,
            'user': user,
            'project': project,
            'hours': hours,
            'is_billable': is_billable,
            'rate': billing_rate,
            'amount': amount,
            'notes': entry.notes
        })
    
    # Convert sets to lists for template
    for proj_data in summary['by_project'].values():
        proj_data['users'] = sorted(list(proj_data['users']))
    
    for user_data in summary['by_user'].values():
        user_data['projects'] = sorted(list(user_data['projects']))
    
    # Sort entries by date
    summary['entries'].sort(key=lambda x: x['date'], reverse=True)
    
    return summary


@billing_bp.route('/api/billing-data')
@role_required(Role.SUPERVISOR)
@company_required
def api_billing_data():
    """API endpoint for billing data (for AJAX updates)"""
    # Get parameters
    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    project_id = request.args.get('project_id', type=int)
    user_id = request.args.get('user_id', type=int)
    
    # Calculate date range
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # Get company settings
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    
    # Get billing data
    billing_data = get_billing_data(
        company_id=g.user.company_id,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
        user_id=user_id
    )
    
    # Format for JSON response
    response_data = {
        'summary': {
            'total_hours': round(billing_data['total_hours'], 2),
            'billable_hours': round(billing_data['billable_hours'], 2),
            'non_billable_hours': round(billing_data['non_billable_hours'], 2),
            'total_amount': round(billing_data['total_amount'], 2),
            'currency': currency
        },
        'by_project': [
            {
                'id': proj_id,
                'name': data['project'].name,
                'code': data['project'].code,
                'total_hours': round(data['total_hours'], 2),
                'billable_hours': round(data['billable_hours'], 2),
                'total_amount': round(data['total_amount'], 2)
            }
            for proj_id, data in billing_data['by_project'].items()
        ],
        'by_user': [
            {
                'id': user_id,
                'name': data['user'].username,
                'total_hours': round(data['total_hours'], 2),
                'billable_hours': round(data['billable_hours'], 2),
                'total_amount': round(data['total_amount'], 2)
            }
            for user_id, data in billing_data['by_user'].items()
        ],
        'daily_totals': [
            {
                'date': date_key,
                'total_hours': round(data['total_hours'], 2),
                'billable_hours': round(data['billable_hours'], 2),
                'total_amount': round(data['total_amount'], 2)
            }
            for date_key, data in sorted(billing_data['by_date'].items())
        ]
    }
    
    return jsonify(response_data)


def export_billing_excel(billing_data, currency, currency_symbol, year, month):
    """Export billing report to Excel format using xlsxwriter"""
    # Create BytesIO object
    excel_file = io.BytesIO()
    
    # Create workbook and formats
    workbook = xlsxwriter.Workbook(excel_file, {'in_memory': True})
    
    # Define formats
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'bg_color': '#667eea',
        'font_color': 'white',
        'border': 1
    })
    
    label_format = workbook.add_format({
        'bold': True
    })
    
    money_format = workbook.add_format({
        'num_format': f'"{currency_symbol}"#,##0.00'
    })
    
    # Summary sheet
    summary_sheet = workbook.add_worksheet('Summary')
    
    # Title
    summary_sheet.merge_range('A1:E1', f'Billing Report - {calendar.month_name[month]} {year}', title_format)
    
    # Summary section
    summary_sheet.write('A3', 'Summary', label_format)
    summary_sheet.write('A4', 'Total Hours:', label_format)
    summary_sheet.write('B4', round(billing_data['total_hours'], 2))
    summary_sheet.write('A5', 'Billable Hours:', label_format)
    summary_sheet.write('B5', round(billing_data['billable_hours'], 2))
    summary_sheet.write('A6', 'Non-Billable Hours:', label_format)
    summary_sheet.write('B6', round(billing_data['non_billable_hours'], 2))
    summary_sheet.write('A7', 'Total Revenue:', label_format)
    summary_sheet.write('B7', round(billing_data['total_amount'], 2), money_format)
    summary_sheet.write('A8', 'Currency:', label_format)
    summary_sheet.write('B8', currency)
    
    # By Project sheet
    project_sheet = workbook.add_worksheet('By Project')
    project_headers = ['Project', 'Code', 'Total Hours', 'Billable Hours', 'Non-Billable Hours', 'Revenue']
    
    # Write headers
    for col, header in enumerate(project_headers):
        project_sheet.write(0, col, header, header_format)
    
    # Write data
    row = 1
    for proj_data in billing_data['by_project'].values():
        project_sheet.write(row, 0, proj_data['project'].name)
        project_sheet.write(row, 1, proj_data['project'].code)
        project_sheet.write(row, 2, round(proj_data['total_hours'], 2))
        project_sheet.write(row, 3, round(proj_data['billable_hours'], 2))
        project_sheet.write(row, 4, round(proj_data['non_billable_hours'], 2))
        project_sheet.write(row, 5, round(proj_data['total_amount'], 2), money_format)
        row += 1
    
    # By User sheet
    user_sheet = workbook.add_worksheet('By User')
    user_headers = ['User', 'Total Hours', 'Billable Hours', 'Non-Billable Hours', 'Revenue']
    
    # Write headers
    for col, header in enumerate(user_headers):
        user_sheet.write(0, col, header, header_format)
    
    # Write data
    row = 1
    for user_data in billing_data['by_user'].values():
        user_sheet.write(row, 0, user_data['user'].username)
        user_sheet.write(row, 1, round(user_data['total_hours'], 2))
        user_sheet.write(row, 2, round(user_data['billable_hours'], 2))
        user_sheet.write(row, 3, round(user_data['non_billable_hours'], 2))
        user_sheet.write(row, 4, round(user_data['total_amount'], 2), money_format)
        row += 1
    
    # Detailed entries sheet
    detail_sheet = workbook.add_worksheet('Detailed Entries')
    detail_headers = ['Date', 'User', 'Project', 'Hours', 'Type', 'Rate', 'Amount', 'Notes']
    
    # Write headers
    for col, header in enumerate(detail_headers):
        detail_sheet.write(0, col, header, header_format)
    
    # Write data
    row = 1
    for entry in billing_data['entries']:
        detail_sheet.write(row, 0, entry['date'].strftime('%Y-%m-%d'))
        detail_sheet.write(row, 1, entry['user'].username)
        detail_sheet.write(row, 2, entry['project'].name)
        detail_sheet.write(row, 3, round(entry['hours'], 2))
        detail_sheet.write(row, 4, 'Billable' if entry['is_billable'] else 'Non-Billable')
        if entry['rate']:
            detail_sheet.write(row, 5, round(entry['rate'], 2), money_format)
        else:
            detail_sheet.write(row, 5, '-')
        if entry['is_billable']:
            detail_sheet.write(row, 6, round(entry['amount'], 2), money_format)
        else:
            detail_sheet.write(row, 6, '-')
        detail_sheet.write(row, 7, entry['notes'] or '-')
        row += 1
    
    # Auto-fit columns
    for worksheet in [summary_sheet, project_sheet, user_sheet, detail_sheet]:
        worksheet.autofit()
    
    # Close workbook
    workbook.close()
    
    # Rewind the buffer
    excel_file.seek(0)
    
    filename = f"billing_report_{year}_{month:02d}.xlsx"
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def export_billing_csv(billing_data, currency, currency_symbol, year, month):
    """Export billing report to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write summary
    writer.writerow([f"Billing Report - {calendar.month_name[month]} {year}"])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Hours", round(billing_data['total_hours'], 2)])
    writer.writerow(["Billable Hours", round(billing_data['billable_hours'], 2)])
    writer.writerow(["Non-Billable Hours", round(billing_data['non_billable_hours'], 2)])
    writer.writerow(["Total Revenue", f"{currency_symbol}{round(billing_data['total_amount'], 2)}"])
    writer.writerow(["Currency", currency])
    writer.writerow([])
    
    # Write detailed entries
    writer.writerow(["Detailed Entries"])
    writer.writerow(["Date", "User", "Project", "Hours", "Type", "Rate", "Amount", "Notes"])
    
    for entry in billing_data['entries']:
        writer.writerow([
            entry['date'].strftime('%Y-%m-%d'),
            entry['user'].username,
            entry['project'].name,
            round(entry['hours'], 2),
            'Billable' if entry['is_billable'] else 'Non-Billable',
            f"{currency_symbol}{round(entry['rate'], 2)}" if entry['rate'] else '-',
            f"{currency_symbol}{round(entry['amount'], 2)}" if entry['is_billable'] else '-',
            entry['notes'] or '-'
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=billing_report_{year}_{month:02d}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response