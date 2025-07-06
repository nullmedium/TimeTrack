# Standard library imports
import os
import re
import tempfile
import zipfile
from datetime import datetime
from urllib.parse import unquote

# Third-party imports
from flask import (Blueprint, Response, abort, flash, g, redirect, request,
                   send_file, url_for)

# Local application imports
from frontmatter_utils import parse_frontmatter
from models import Note, db
from routes.auth import company_required, login_required

# Create blueprint
notes_download_bp = Blueprint('notes_download', __name__)


@notes_download_bp.route('/notes/<slug>/download/<format>')
@login_required
@company_required
def download_note(slug, format):
    """Download a note in various formats"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_view(g.user):
        abort(403)
    
    # Prepare filename
    safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', note.title)
    timestamp = datetime.now().strftime('%Y%m%d')
    
    if format == 'md':
        # Download as Markdown with frontmatter
        content = note.content
        response = Response(content, mimetype='text/markdown')
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}_{timestamp}.md"'
        return response
    
    elif format == 'html':
        # Download as HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{note.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 2rem; }}
        h1, h2, h3 {{ margin-top: 2rem; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 1rem; color: #666; }}
        .metadata {{ background: #f9f9f9; padding: 1rem; border-radius: 5px; margin-bottom: 2rem; }}
        .metadata dl {{ margin: 0; }}
        .metadata dt {{ font-weight: bold; display: inline-block; width: 120px; }}
        .metadata dd {{ display: inline; margin: 0; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h1>{note.title}</h1>
        <dl>
            <dt>Author:</dt><dd>{note.created_by.username}</dd><br>
            <dt>Created:</dt><dd>{note.created_at.strftime('%Y-%m-%d %H:%M')}</dd><br>
            <dt>Updated:</dt><dd>{note.updated_at.strftime('%Y-%m-%d %H:%M')}</dd><br>
            <dt>Visibility:</dt><dd>{note.visibility.value}</dd><br>
            {'<dt>Folder:</dt><dd>' + note.folder + '</dd><br>' if note.folder else ''}
            {'<dt>Tags:</dt><dd>' + note.tags + '</dd><br>' if note.tags else ''}
        </dl>
    </div>
    {note.render_html()}
</body>
</html>"""
        response = Response(html_content, mimetype='text/html')
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}_{timestamp}.html"'
        return response
    
    elif format == 'txt':
        # Download as plain text
        metadata, body = parse_frontmatter(note.content)
        
        # Create plain text version
        text_content = f"{note.title}\n{'=' * len(note.title)}\n\n"
        text_content += f"Author: {note.created_by.username}\n"
        text_content += f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        text_content += f"Updated: {note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        text_content += f"Visibility: {note.visibility.value}\n"
        if note.folder:
            text_content += f"Folder: {note.folder}\n"
        if note.tags:
            text_content += f"Tags: {note.tags}\n"
        text_content += "\n" + "-" * 40 + "\n\n"
        
        # Remove markdown formatting
        text_body = body
        # Remove headers markdown
        text_body = re.sub(r'^#+\s+', '', text_body, flags=re.MULTILINE)
        # Remove emphasis
        text_body = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text_body)
        text_body = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text_body)
        # Remove links but keep text
        text_body = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text_body)
        # Remove images
        text_body = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[Image: \1]', text_body)
        # Remove code blocks markers
        text_body = re.sub(r'```[^`]*```', lambda m: m.group(0).replace('```', ''), text_body, flags=re.DOTALL)
        text_body = re.sub(r'`([^`]+)`', r'\1', text_body)
        
        text_content += text_body
        
        response = Response(text_content, mimetype='text/plain')
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}_{timestamp}.txt"'
        return response
    
    else:
        abort(404)


@notes_download_bp.route('/notes/download-bulk', methods=['POST'])
@login_required
@company_required
def download_notes_bulk():
    """Download multiple notes as a zip file"""
    note_ids = request.form.getlist('note_ids[]')
    format = request.form.get('format', 'md')
    
    if not note_ids:
        flash('No notes selected for download', 'error')
        return redirect(url_for('notes.notes_list'))
    
    # Create a temporary file for the zip
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_file.name, 'w') as zipf:
            for note_id in note_ids:
                note = Note.query.filter_by(id=int(note_id), company_id=g.user.company_id).first()
                if note and note.can_user_view(g.user):
                    # Get content based on format
                    safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', note.title)
                    
                    if format == 'md':
                        content = note.content
                        filename = f"{safe_filename}.md"
                    elif format == 'html':
                        content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{note.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 2rem; }}
        h1, h2, h3 {{ margin-top: 2rem; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 1rem; color: #666; }}
    </style>
</head>
<body>
    <h1>{note.title}</h1>
    {note.render_html()}
</body>
</html>"""
                        filename = f"{safe_filename}.html"
                    else:  # txt
                        metadata, body = parse_frontmatter(note.content)
                        content = f"{note.title}\n{'=' * len(note.title)}\n\n{body}"
                        filename = f"{safe_filename}.txt"
                    
                    # Add file to zip
                    zipf.writestr(filename, content)
        
        # Send the zip file
        temp_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'notes_{timestamp}.zip'
        )
        
    finally:
        # Clean up temp file after sending
        os.unlink(temp_file.name)


@notes_download_bp.route('/notes/folder/<path:folder_path>/download/<format>')
@login_required
@company_required
def download_folder(folder_path, format):
    """Download all notes in a folder as a zip file"""
    # Decode folder path (replace URL encoding)
    folder_path = unquote(folder_path)
    
    # Get all notes in this folder
    notes = Note.query.filter_by(
        company_id=g.user.company_id,
        folder=folder_path,
        is_archived=False
    ).all()
    
    # Filter notes user can view
    viewable_notes = [note for note in notes if note.can_user_view(g.user)]
    
    if not viewable_notes:
        flash('No notes found in this folder or you don\'t have permission to view them.', 'warning')
        return redirect(url_for('notes.notes_list'))
    
    # Create a temporary file for the zip
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_file.name, 'w') as zipf:
            for note in viewable_notes:
                # Get content based on format
                safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', note.title)
                
                if format == 'md':
                    content = note.content
                    filename = f"{safe_filename}.md"
                elif format == 'html':
                    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{note.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 2rem; }}
        h1, h2, h3 {{ margin-top: 2rem; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 1rem; color: #666; }}
        .metadata {{ background: #f9f9f9; padding: 1rem; border-radius: 5px; margin-bottom: 2rem; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h1>{note.title}</h1>
        <p>Author: {note.created_by.username} | Created: {note.created_at.strftime('%Y-%m-%d %H:%M')} | Folder: {note.folder}</p>
    </div>
    {note.render_html()}
</body>
</html>"""
                    filename = f"{safe_filename}.html"
                else:  # txt
                    metadata, body = parse_frontmatter(note.content)
                    # Remove markdown formatting
                    text_body = body
                    text_body = re.sub(r'^#+\s+', '', text_body, flags=re.MULTILINE)
                    text_body = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text_body)
                    text_body = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text_body)
                    text_body = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text_body)
                    text_body = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[Image: \1]', text_body)
                    text_body = re.sub(r'```[^`]*```', lambda m: m.group(0).replace('```', ''), text_body, flags=re.DOTALL)
                    text_body = re.sub(r'`([^`]+)`', r'\1', text_body)
                    
                    content = f"{note.title}\n{'=' * len(note.title)}\n\n"
                    content += f"Author: {note.created_by.username}\n"
                    content += f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    content += f"Folder: {note.folder}\n\n"
                    content += "-" * 40 + "\n\n"
                    content += text_body
                    filename = f"{safe_filename}.txt"
                
                # Add file to zip
                zipf.writestr(filename, content)
        
        # Send the zip file
        temp_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_folder_name = re.sub(r'[^a-zA-Z0-9_-]', '_', folder_path.replace('/', '_'))
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{safe_folder_name}_notes_{timestamp}.zip'
        )
        
    finally:
        # Clean up temp file after sending
        os.unlink(temp_file.name)