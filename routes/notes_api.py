# Standard library imports
from datetime import datetime, timezone

# Third-party imports
from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy import and_, or_

# Local application imports
from models import Note, NoteFolder, NoteLink, NoteVisibility, db
from routes.auth import company_required, login_required

# Create blueprint
notes_api_bp = Blueprint('notes_api', __name__, url_prefix='/api/notes')


@notes_api_bp.route('/folder-details')
@login_required
@company_required
def api_folder_details():
    """Get folder details including note count"""
    folder_path = request.args.get('folder', '')
    
    # Get note count for this folder
    note_count = Note.query.filter_by(
        company_id=g.user.company_id,
        folder=folder_path,
        is_archived=False
    ).count()
    
    # Check if folder exists in NoteFolder table
    folder = NoteFolder.query.filter_by(
        company_id=g.user.company_id,
        path=folder_path
    ).first()
    
    return jsonify({
        'success': True,
        'folder': {
            'path': folder_path,
            'name': folder_path.split('/')[-1] if folder_path else 'Root',
            'exists': folder is not None,
            'note_count': note_count,
            'created_at': folder.created_at.isoformat() if folder else None
        }
    })


@notes_api_bp.route('/folders', methods=['POST'])
@login_required
@company_required
def api_create_folder():
    """Create a new folder"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    folder_name = data.get('name', '').strip()
    parent_path = data.get('parent', '').strip()
    description = data.get('description', '').strip()
    
    if not folder_name:
        return jsonify({'success': False, 'message': 'Folder name is required'}), 400
    
    # Validate folder name
    if '/' in folder_name:
        return jsonify({'success': False, 'message': 'Folder name cannot contain /'}), 400
    
    # Build full path
    if parent_path:
        full_path = f"{parent_path}/{folder_name}"
    else:
        full_path = folder_name
    
    # Check if folder already exists
    existing = NoteFolder.query.filter_by(
        company_id=g.user.company_id,
        path=full_path
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Folder already exists'}), 400
    
    # Create folder
    folder = NoteFolder(
        name=folder_name,
        path=full_path,
        parent_path=parent_path if parent_path else None,
        description=description if description else None,
        company_id=g.user.company_id,
        created_by_id=g.user.id
    )
    
    db.session.add(folder)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Folder created successfully',
        'folder': {
            'path': folder.path,
            'name': folder_name
        }
    })


@notes_api_bp.route('/folders', methods=['PUT'])
@login_required
@company_required
def api_rename_folder():
    """Rename a folder"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    old_path = data.get('old_path', '').strip()
    new_name = data.get('new_name', '').strip()
    
    if not old_path or not new_name:
        return jsonify({'success': False, 'message': 'Both old path and new name are required'}), 400
    
    # Validate new name
    if '/' in new_name:
        return jsonify({'success': False, 'message': 'Folder name cannot contain /'}), 400
    
    # Find the folder
    folder = NoteFolder.query.filter_by(
        company_id=g.user.company_id,
        path=old_path
    ).first()
    
    if not folder:
        return jsonify({'success': False, 'message': 'Folder not found'}), 404
    
    # Build new path
    path_parts = old_path.split('/')
    path_parts[-1] = new_name
    new_path = '/'.join(path_parts)
    
    # Check if new path already exists
    existing = NoteFolder.query.filter_by(
        company_id=g.user.company_id,
        path=new_path
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'A folder with this name already exists'}), 400
    
    # Update folder path
    folder.path = new_path
    
    # Update all notes in this folder
    Note.query.filter_by(
        company_id=g.user.company_id,
        folder=old_path
    ).update({Note.folder: new_path})
    
    # Update all subfolders
    subfolders = NoteFolder.query.filter(
        NoteFolder.company_id == g.user.company_id,
        NoteFolder.path.like(f"{old_path}/%")
    ).all()
    
    for subfolder in subfolders:
        subfolder.path = subfolder.path.replace(old_path, new_path, 1)
    
    # Update all notes in subfolders
    notes_in_subfolders = Note.query.filter(
        Note.company_id == g.user.company_id,
        Note.folder.like(f"{old_path}/%")
    ).all()
    
    for note in notes_in_subfolders:
        note.folder = note.folder.replace(old_path, new_path, 1)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Folder renamed successfully',
        'folder': {
            'old_path': old_path,
            'new_path': new_path
        }
    })


@notes_api_bp.route('/folders', methods=['DELETE'])
@login_required
@company_required
def api_delete_folder():
    """Delete a folder"""
    folder_path = request.args.get('path', '').strip()
    
    if not folder_path:
        return jsonify({'success': False, 'message': 'Folder path is required'}), 400
    
    # Check if folder has notes
    note_count = Note.query.filter_by(
        company_id=g.user.company_id,
        folder=folder_path,
        is_archived=False
    ).count()
    
    if note_count > 0:
        return jsonify({
            'success': False,
            'message': f'Cannot delete folder with {note_count} notes. Please move or delete the notes first.'
        }), 400
    
    # Find and delete the folder
    folder = NoteFolder.query.filter_by(
        company_id=g.user.company_id,
        path=folder_path
    ).first()
    
    if folder:
        db.session.delete(folder)
        db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Folder deleted successfully'
    })


@notes_api_bp.route('/<slug>/folder', methods=['PUT'])
@login_required
@company_required
def update_note_folder(slug):
    """Update a note's folder via drag and drop"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_edit(g.user):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    new_folder = data.get('folder', '').strip()
    
    # Update note folder
    note.folder = new_folder if new_folder else None
    note.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Note moved successfully'
    })


@notes_api_bp.route('/<int:note_id>/move', methods=['POST'])
@login_required
@company_required
def move_note_to_folder(note_id):
    """Move a note to a different folder (used by drag and drop)"""
    note = Note.query.filter_by(id=note_id, company_id=g.user.company_id).first()
    
    if not note:
        return jsonify({'success': False, 'error': 'Note not found'}), 404
    
    # Check permissions
    if not note.can_user_edit(g.user):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    data = request.get_json()
    new_folder = data.get('folder', '').strip()
    
    # Update note folder
    note.folder = new_folder if new_folder else None
    note.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Note moved successfully',
        'folder': note.folder or ''
    })


@notes_api_bp.route('/<int:note_id>/tags', methods=['POST'])
@login_required
@company_required
def add_tags_to_note(note_id):
    """Add tags to a note"""
    note = Note.query.filter_by(id=note_id, company_id=g.user.company_id).first()
    
    if not note:
        return jsonify({'success': False, 'message': 'Note not found'}), 404
    
    # Check permissions
    if not note.can_user_edit(g.user):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    new_tags = data.get('tags', '').strip()
    
    if not new_tags:
        return jsonify({'success': False, 'message': 'No tags provided'}), 400
    
    # Merge with existing tags
    existing_tags = note.get_tags_list()
    new_tag_list = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
    
    # Combine and deduplicate
    all_tags = list(set(existing_tags + new_tag_list))
    
    # Update note
    note.tags = ', '.join(sorted(all_tags))
    note.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Tags added successfully',
        'tags': all_tags
    })


@notes_api_bp.route('/<int:note_id>/link', methods=['POST'])
@login_required
@company_required
def link_notes(note_id):
    """Create a link between two notes"""
    source_note = Note.query.filter_by(id=note_id, company_id=g.user.company_id).first()
    
    if not source_note:
        return jsonify({'success': False, 'message': 'Source note not found'}), 404
    
    # Check permissions
    if not source_note.can_user_edit(g.user):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    target_note_id = data.get('target_note_id')
    link_type = data.get('link_type', 'related')
    
    if not target_note_id:
        return jsonify({'success': False, 'message': 'Target note ID is required'}), 400
    
    # Get target note
    target_note = Note.query.filter_by(id=target_note_id, company_id=g.user.company_id).first()
    
    if not target_note:
        return jsonify({'success': False, 'message': 'Target note not found'}), 404
    
    # Check if user can view target note
    if not target_note.can_user_view(g.user):
        return jsonify({'success': False, 'message': 'You cannot link to a note you cannot view'}), 403
    
    # Check if link already exists
    existing_link = NoteLink.query.filter_by(
        source_note_id=source_note.id,
        target_note_id=target_note.id
    ).first()
    
    if existing_link:
        return jsonify({'success': False, 'message': 'Link already exists'}), 400
    
    # Create link
    link = NoteLink(
        source_note_id=source_note.id,
        target_note_id=target_note.id,
        link_type=link_type,
        created_by_id=g.user.id
    )
    
    db.session.add(link)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notes linked successfully'
    })


@notes_api_bp.route('/<int:note_id>/link', methods=['DELETE'])
@login_required
@company_required
def unlink_notes(note_id):
    """Remove a link between two notes"""
    source_note = Note.query.filter_by(id=note_id, company_id=g.user.company_id).first()
    
    if not source_note:
        return jsonify({'success': False, 'message': 'Source note not found'}), 404
    
    # Check permissions
    if not source_note.can_user_edit(g.user):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    target_note_id = data.get('target_note_id')
    
    if not target_note_id:
        return jsonify({'success': False, 'message': 'Target note ID is required'}), 400
    
    # Find and delete the link (check both directions)
    link = NoteLink.query.filter(
        or_(
            and_(
                NoteLink.source_note_id == source_note.id,
                NoteLink.target_note_id == target_note_id
            ),
            and_(
                NoteLink.source_note_id == target_note_id,
                NoteLink.target_note_id == source_note.id
            )
        )
    ).first()
    
    if not link:
        return jsonify({'success': False, 'message': 'Link not found'}), 404
    
    db.session.delete(link)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Link removed successfully'
    })