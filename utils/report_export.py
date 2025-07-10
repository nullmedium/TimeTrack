"""
Report export utilities for the Advanced Report Engine.
Handles exporting report data to various file formats (CSV, Excel, PDF).
"""

import io
import csv
import pandas as pd
from flask import Response, send_file
from datetime import datetime
import json
from typing import Dict, Any, List


def export_report_to_csv(report_data: Dict[str, Any], report_name: str) -> Response:
    """Export report data to CSV format."""
    output = io.StringIO()
    
    # Extract the data from the report result
    if 'data' in report_data and isinstance(report_data['data'], list) and report_data['data']:
        # Use the first row to determine fieldnames
        fieldnames = list(report_data['data'][0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        # Write metadata as comments
        output.write(f"# Report: {report_name}\n")
        output.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if 'metadata' in report_data:
            output.write(f"# Period: {report_data['metadata'].get('period', 'N/A')}\n")
            output.write(f"# Total Records: {report_data['metadata'].get('total_records', len(report_data['data']))}\n")
        output.write("#\n")
        
        # Write the actual data
        writer.writeheader()
        writer.writerows(report_data['data'])
    else:
        # Handle edge case where data might be in a different format
        output.write("No data available for export\n")
    
    output.seek(0)
    filename = f"{report_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


def export_report_to_excel(report_data: Dict[str, Any], report_name: str) -> Response:
    """Export report data to Excel format with formatting."""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Main data sheet
        if 'data' in report_data and isinstance(report_data['data'], list) and report_data['data']:
            df = pd.DataFrame(report_data['data'])
            df.to_excel(writer, sheet_name='Report Data', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Report Data']
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })
            
            # Apply header formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
            
            # Add number formatting for numeric columns
            for i, col in enumerate(df.columns):
                if df[col].dtype in ['float64', 'int64']:
                    if 'percentage' in col.lower() or 'percent' in col.lower() or '%' in col:
                        # Percentage format
                        percent_format = workbook.add_format({'num_format': '0.00%'})
                        worksheet.set_column(i, i, min(max_len, 50), percent_format)
                    elif 'currency' in col.lower() or 'amount' in col.lower() or '$' in col:
                        # Currency format
                        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
                        worksheet.set_column(i, i, min(max_len, 50), currency_format)
                    else:
                        # General number format
                        number_format = workbook.add_format({'num_format': '#,##0.00'})
                        worksheet.set_column(i, i, min(max_len, 50), number_format)
        
        # Metadata sheet
        if 'metadata' in report_data:
            metadata_list = []
            for key, value in report_data['metadata'].items():
                metadata_list.append({
                    'Property': key.replace('_', ' ').title(),
                    'Value': str(value)
                })
            metadata_list.append({
                'Property': 'Generated At',
                'Value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            metadata_df = pd.DataFrame(metadata_list)
            metadata_df.to_excel(writer, sheet_name='Report Info', index=False)
            
            # Format metadata sheet
            worksheet_meta = writer.sheets['Report Info']
            for i, col in enumerate(metadata_df.columns):
                max_len = max(metadata_df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet_meta.set_column(i, i, min(max_len, 50))
                worksheet_meta.write(0, i, col, header_format)
        
        # Charts data sheet (if available)
        if 'charts' in report_data:
            charts_data = []
            for i, chart in enumerate(report_data['charts']):
                charts_data.append({
                    'Chart': f"Chart {i+1}",
                    'Type': chart.get('type', 'Unknown'),
                    'Title': chart.get('title', 'Untitled'),
                    'Data Points': len(chart.get('data', []))
                })
            
            if charts_data:
                charts_df = pd.DataFrame(charts_data)
                charts_df.to_excel(writer, sheet_name='Charts Summary', index=False)
                
                worksheet_charts = writer.sheets['Charts Summary']
                for i, col in enumerate(charts_df.columns):
                    max_len = max(charts_df[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet_charts.set_column(i, i, min(max_len, 50))
                    worksheet_charts.write(0, i, col, header_format)
    
    output.seek(0)
    filename = f"{report_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def flatten_nested_data(data: Any, parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten nested dictionaries for CSV/Excel export."""
    items = []
    
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_nested_data(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to comma-separated strings
                items.append((new_key, ', '.join(str(item) for item in v)))
            else:
                items.append((new_key, v))
    else:
        items.append((parent_key, data))
    
    return dict(items)


def prepare_report_data_for_export(report_result: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare report data for export by flattening nested structures."""
    prepared_data = report_result.copy()
    
    # If data contains nested structures, flatten them
    if 'data' in prepared_data and isinstance(prepared_data['data'], list):
        flattened_data = []
        for row in prepared_data['data']:
            if isinstance(row, dict):
                flattened_data.append(flatten_nested_data(row))
            else:
                flattened_data.append(row)
        prepared_data['data'] = flattened_data
    
    return prepared_data