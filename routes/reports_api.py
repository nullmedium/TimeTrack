"""
Reports API - RESTful endpoints for the Advanced Report Engine.
"""

from flask import Blueprint, request, jsonify, g, send_file
from datetime import datetime, timedelta
import io
import json

from models import db, ReportTemplate, SavedReport, ReportShare, ReportExportHistory
from analytics.engine import ReportBuilder
from routes.auth import login_required, admin_required

reports_api = Blueprint('reports_api', __name__)


@reports_api.route('/api/reports/templates', methods=['GET'])
@login_required
def get_report_templates():
    """Get available report templates."""
    try:
        builder = ReportBuilder(db.session, g.user)
        templates = builder.get_available_templates()
        
        return jsonify({
            'success': True,
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/templates/<int:template_id>', methods=['GET'])
@login_required
def get_report_template(template_id):
    """Get a specific report template."""
    try:
        template = db.session.query(ReportTemplate).filter_by(id=template_id).first()
        
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
            
        # Check access
        if not (template.is_public or 
                template.company_id == g.user.company_id or 
                template.created_by == g.user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports', methods=['GET'])
@login_required
def get_user_reports():
    """Get user's saved reports."""
    try:
        builder = ReportBuilder(db.session, g.user)
        include_shared = request.args.get('include_shared', 'true').lower() == 'true'
        reports = builder.get_user_reports(include_shared)
        
        return jsonify({
            'success': True,
            'reports': [r.to_dict() for r in reports]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports', methods=['POST'])
@login_required
def create_report():
    """Create a new report."""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Report name required'}), 400
            
        builder = ReportBuilder(db.session, g.user)
        report = builder.create_report(
            name=data['name'],
            template_id=data.get('template_id'),
            config=data.get('config')
        )
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report(report_id):
    """Get a specific report configuration."""
    try:
        report = db.session.query(SavedReport).filter_by(id=report_id).first()
        
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
            
        # Check access
        builder = ReportBuilder(db.session, g.user)
        if not builder._can_access_report(report):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>', methods=['PUT'])
@login_required
def update_report(report_id):
    """Update a report configuration."""
    try:
        data = request.get_json()
        builder = ReportBuilder(db.session, g.user)
        
        report = builder.update_report(report_id, data)
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """Delete a report."""
    try:
        report = db.session.query(SavedReport).filter_by(
            id=report_id,
            user_id=g.user.id
        ).first()
        
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
            
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>/execute', methods=['POST'])
@login_required
def execute_report(report_id):
    """Execute a report and return the data."""
    try:
        data = request.get_json() or {}
        builder = ReportBuilder(db.session, g.user)
        
        # Parse date range if provided
        date_range = None
        if data.get('start_date') or data.get('end_date'):
            date_range = {}
            if data.get('start_date'):
                date_range['start'] = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if data.get('end_date'):
                date_range['end'] = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        # Execute report
        result = builder.execute_report(
            report_id,
            date_range=date_range,
            additional_filters=data.get('filters')
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>/share', methods=['POST'])
@login_required
def share_report(report_id):
    """Share a report with users or teams."""
    try:
        data = request.get_json()
        
        report = db.session.query(SavedReport).filter_by(
            id=report_id,
            user_id=g.user.id
        ).first()
        
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        # Create share
        share = ReportShare(
            report_id=report_id,
            shared_by=g.user.id,
            permission=data.get('permission', 'view')
        )
        
        if data.get('user_id'):
            share.shared_with_user_id = data['user_id']
        elif data.get('team_id'):
            share.shared_with_team_id = data['team_id']
        else:
            return jsonify({'success': False, 'error': 'Must specify user_id or team_id'}), 400
        
        # Set expiration if provided
        if data.get('expires_in_days'):
            share.expires_at = datetime.utcnow() + timedelta(days=data['expires_in_days'])
        
        db.session.add(share)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'share': share.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>/shares', methods=['GET'])
@login_required
def get_report_shares(report_id):
    """Get shares for a report."""
    try:
        report = db.session.query(SavedReport).filter_by(
            id=report_id,
            user_id=g.user.id
        ).first()
        
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        shares = [s.to_dict() for s in report.shares if not s.is_expired()]
        
        return jsonify({
            'success': True,
            'shares': shares
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/shares/<int:share_id>', methods=['DELETE'])
@login_required
def delete_share(share_id):
    """Remove a report share."""
    try:
        share = db.session.query(ReportShare).filter_by(id=share_id).first()
        
        if not share:
            return jsonify({'success': False, 'error': 'Share not found'}), 404
        
        # Check permissions
        if share.report.user_id != g.user.id and share.shared_by != g.user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        db.session.delete(share)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/<int:report_id>/export/<format>', methods=['POST'])
@login_required
def export_report(report_id, format):
    """Export a report in various formats."""
    try:
        if format not in ['pdf', 'excel', 'csv', 'json']:
            return jsonify({'success': False, 'error': 'Invalid format'}), 400
        
        # Execute report first
        data = request.get_json() or {}
        builder = ReportBuilder(db.session, g.user)
        
        # Parse date range
        date_range = None
        if data.get('start_date') or data.get('end_date'):
            date_range = {}
            if data.get('start_date'):
                date_range['start'] = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if data.get('end_date'):
                date_range['end'] = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        result = builder.execute_report(
            report_id,
            date_range=date_range,
            additional_filters=data.get('filters')
        )
        
        # Export based on format
        if format == 'json':
            output = io.BytesIO()
            output.write(json.dumps(result, indent=2).encode())
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'report_{report_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
        
        # For other formats, we'll need to implement exporters
        # For now, return a placeholder
        return jsonify({
            'success': False,
            'error': f'{format} export not yet implemented'
        }), 501
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/templates', methods=['POST'])
@admin_required
def create_template():
    """Create a new report template (admin only)."""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Template name required'}), 400
        
        template = ReportTemplate(
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'custom'),
            template_config=data.get('template_config', {}),
            is_public=data.get('is_public', False),
            created_by=g.user.id,
            company_id=g.user.company_id
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_api.route('/api/reports/templates/<int:template_id>', methods=['PUT'])
@admin_required
def update_template(template_id):
    """Update a report template (admin only)."""
    try:
        data = request.get_json()
        template = db.session.query(ReportTemplate).filter_by(id=template_id).first()
        
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Only allow updating non-system templates
        if template.is_system:
            return jsonify({'success': False, 'error': 'Cannot modify system templates'}), 403
        
        # Update fields
        if 'name' in data:
            template.name = data['name']
        if 'description' in data:
            template.description = data['description']
        if 'category' in data:
            template.category = data['category']
        if 'template_config' in data:
            template.template_config = data['template_config']
        if 'is_public' in data:
            template.is_public = data['is_public']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500