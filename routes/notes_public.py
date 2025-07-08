"""
Public routes for viewing shared notes without authentication
"""

from flask import Blueprint, render_template, abort, request, session, jsonify
from werkzeug.security import check_password_hash
from models import NoteShare, db

notes_public_bp = Blueprint('notes_public', __name__, url_prefix='/public/notes')


@notes_public_bp.route('/<token>')
def view_shared_note(token):
    """View a publicly shared note"""
    # Find the share
    share = NoteShare.query.filter_by(token=token).first()
    if not share:
        abort(404, "Share link not found")
    
    # Check if share is valid
    if not share.is_valid():
        if share.is_expired():
            abort(410, "This share link has expired")
        elif share.is_view_limit_reached():
            abort(410, "This share link has reached its view limit")
        else:
            abort(404, "This share link is no longer valid")
    
    # Check password if required
    if share.password_hash:
        # Check if password was already verified in session
        verified_shares = session.get('verified_shares', [])
        if share.id not in verified_shares:
            # For GET request, show password form
            if request.method == 'GET':
                return render_template('notes/share_password.html', 
                                     token=token,
                                     note_title=share.note.title)
    
    # Record access
    share.record_access()
    db.session.commit()
    
    # Render the note (read-only view)
    return render_template('notes/public_view.html', 
                         note=share.note,
                         share=share)


@notes_public_bp.route('/<token>/verify', methods=['POST'])
def verify_share_password(token):
    """Verify password for a protected share"""
    share = NoteShare.query.filter_by(token=token).first()
    if not share:
        abort(404, "Share link not found")
    
    if not share.is_valid():
        abort(410, "This share link is no longer valid")
    
    password = request.form.get('password', '')
    
    if share.check_password(password):
        # Store verification in session
        verified_shares = session.get('verified_shares', [])
        if share.id not in verified_shares:
            verified_shares.append(share.id)
            session['verified_shares'] = verified_shares
        
        # Redirect to the note view
        return jsonify({'success': True, 'redirect': f'/public/notes/{token}'})
    else:
        return jsonify({'success': False, 'error': 'Invalid password'}), 401


@notes_public_bp.route('/<token>/download/<format>')
def download_shared_note(token, format):
    """Download a shared note in various formats"""
    share = NoteShare.query.filter_by(token=token).first()
    if not share:
        abort(404, "Share link not found")
    
    if not share.is_valid():
        abort(410, "This share link is no longer valid")
    
    # Check password protection
    if share.password_hash:
        verified_shares = session.get('verified_shares', [])
        if share.id not in verified_shares:
            abort(403, "Password verification required")
    
    # Record access
    share.record_access()
    db.session.commit()
    
    # Generate download based on format
    from flask import Response, send_file
    import markdown
    import tempfile
    import os
    from datetime import datetime
    
    note = share.note
    
    if format == 'md':
        # Markdown download
        response = Response(note.content, mimetype='text/markdown')
        response.headers['Content-Disposition'] = f'attachment; filename="{note.slug}.md"'
        return response
    
    elif format == 'html':
        # HTML download
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{note.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 2rem; }}
        h1, h2, h3, h4, h5, h6 {{ margin-top: 2rem; margin-bottom: 1rem; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin-left: 0; padding-left: 1rem; color: #666; }}
    </style>
</head>
<body>
    <h1>{note.title}</h1>
    <p><em>Created: {note.created_at.strftime('%B %d, %Y')}</em></p>
    {note.render_html()}
</body>
</html>"""
        response = Response(html_content, mimetype='text/html')
        response.headers['Content-Disposition'] = f'attachment; filename="{note.slug}.html"'
        return response
    
    elif format == 'pdf':
        # PDF download using weasyprint
        try:
            import weasyprint
            
            # Generate HTML first
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{note.title}</title>
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; }}
        h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5rem; margin-bottom: 0.75rem; page-break-after: avoid; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.9em; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; page-break-inside: avoid; }}
        blockquote {{ border-left: 4px solid #ddd; margin-left: 0; padding-left: 1rem; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #f4f4f4; font-weight: bold; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{note.title}</h1>
    <p><em>Created: {note.created_at.strftime('%B %d, %Y')}</em></p>
    {note.render_html()}
</body>
</html>"""
            
            # Create temporary file for PDF
            temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
            
            # Generate PDF
            weasyprint.HTML(string=html_content).write_pdf(temp_file.name)
            temp_file.close()
            
            # Send file
            response = send_file(
                temp_file.name,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{note.slug}.pdf'
            )
            
            # Clean up temp file after sending
            os.unlink(temp_file.name)
            
            return response
            
        except ImportError:
            # If weasyprint is not installed, return error
            abort(500, "PDF generation not available")
    
    else:
        abort(400, "Invalid format")