# Standard library imports
from datetime import datetime, timezone

# Third-party imports
from flask import (Blueprint, abort, flash, g, jsonify, redirect,
                   render_template, request, url_for)
from sqlalchemy import and_, or_

# Local application imports
from models import (Note, NoteFolder, NoteLink, NoteVisibility, Project,
                   Task, db)
from routes.auth import company_required, login_required

# Create blueprint
notes_bp = Blueprint('notes', __name__, url_prefix='/notes')


@notes_bp.route('')
@login_required
@company_required
def notes_list():
    """List all notes with optional filtering"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Notes list route called")
    
    # Get filter parameters
    folder_filter = request.args.get('folder', '')
    tag_filter = request.args.get('tag', '')
    visibility_filter = request.args.get('visibility', '')
    search_query = request.args.get('search', '')
    
    # Base query - only non-archived notes for the user's company
    query = Note.query.filter_by(
        company_id=g.user.company_id,
        is_archived=False
    )
    
    # Apply folder filter
    if folder_filter:
        query = query.filter_by(folder=folder_filter)
    
    # Apply tag filter
    if tag_filter:
        query = query.filter(Note.tags.contains(tag_filter))
    
    # Apply visibility filter
    if visibility_filter:
        if visibility_filter == 'private':
            query = query.filter_by(visibility=NoteVisibility.PRIVATE, created_by_id=g.user.id)
        elif visibility_filter == 'team':
            query = query.filter(
                and_(
                    Note.visibility == NoteVisibility.TEAM,
                    or_(
                        Note.created_by.has(team_id=g.user.team_id),
                        Note.created_by_id == g.user.id
                    )
                )
            )
        elif visibility_filter == 'company':
            query = query.filter_by(visibility=NoteVisibility.COMPANY)
    else:
        # Default visibility filtering - show notes user can see
        query = query.filter(
            or_(
                # Private notes created by user
                and_(Note.visibility == NoteVisibility.PRIVATE, Note.created_by_id == g.user.id),
                # Team notes from user's team
                and_(Note.visibility == NoteVisibility.TEAM, Note.created_by.has(team_id=g.user.team_id)),
                # Company notes
                Note.visibility == NoteVisibility.COMPANY
            )
        )
    
    # Apply search filter
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
                Note.tags.ilike(search_pattern)
            )
        )
    
    # Order by pinned first, then by updated date
    notes = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()
    
    # Get all folders for the sidebar
    all_folders = NoteFolder.query.filter_by(
        company_id=g.user.company_id
    ).order_by(NoteFolder.path).all()
    
    # Build folder tree structure
    folder_tree = {}
    folder_counts = {}
    
    # Count notes per folder
    folder_note_counts = db.session.query(
        Note.folder, db.func.count(Note.id)
    ).filter_by(
        company_id=g.user.company_id,
        is_archived=False
    ).group_by(Note.folder).all()
    
    for folder, count in folder_note_counts:
        if folder:
            folder_counts[folder] = count
    
    # Build folder tree structure
    for folder in all_folders:
        parts = folder.path.split('/')
        current = folder_tree
        
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Leaf folder - use full path as key
                current[folder.path] = {}
            else:
                # Navigate to parent using full path
                parent_path = '/'.join(parts[:i+1])
                if parent_path not in current:
                    current[parent_path] = {}
                current = current[parent_path]
    
    # Get all unique tags
    all_notes_for_tags = Note.query.filter_by(
        company_id=g.user.company_id,
        is_archived=False
    ).all()
    
    all_tags = set()
    tag_counts = {}
    
    for note in all_notes_for_tags:
        if note.tags:
            note_tags = note.get_tags_list()
            for tag in note_tags:
                all_tags.add(tag)
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    all_tags = sorted(list(all_tags))
    
    # Count notes by visibility
    visibility_counts = {
        'private': Note.query.filter_by(
            company_id=g.user.company_id,
            visibility=NoteVisibility.PRIVATE,
            created_by_id=g.user.id,
            is_archived=False
        ).count(),
        'team': Note.query.filter(
            Note.company_id == g.user.company_id,
            Note.visibility == NoteVisibility.TEAM,
            Note.created_by.has(team_id=g.user.team_id),
            Note.is_archived == False
        ).count(),
        'company': Note.query.filter_by(
            company_id=g.user.company_id,
            visibility=NoteVisibility.COMPANY,
            is_archived=False
        ).count()
    }
    
    try:
        logger.info(f"Rendering template with {len(notes)} notes, folder_tree type: {type(folder_tree)}")
        return render_template('notes_list.html',
                             notes=notes,
                             folder_tree=folder_tree,
                             folder_counts=folder_counts,
                             all_tags=all_tags,
                             tag_counts=tag_counts,
                             visibility_counts=visibility_counts,
                             folder_filter=folder_filter,
                             tag_filter=tag_filter,
                             visibility_filter=visibility_filter,
                             search_query=search_query,
                             title='Notes')
    except Exception as e:
        logger.error(f"Error rendering notes template: {str(e)}", exc_info=True)
        raise


@notes_bp.route('/new', methods=['GET', 'POST'])
@login_required
@company_required
def create_note():
    """Create a new note"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        visibility = request.form.get('visibility', 'Private')
        folder = request.form.get('folder', '').strip()
        tags = request.form.get('tags', '').strip()
        project_id = request.form.get('project_id')
        task_id = request.form.get('task_id')
        is_pinned = request.form.get('is_pinned') == '1'
        
        # Validate
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('notes.create_note'))
        
        if not content:
            flash('Content is required', 'error')
            return redirect(url_for('notes.create_note'))
        
        # Validate visibility
        try:
            visibility_enum = NoteVisibility[visibility.upper()]
        except KeyError:
            visibility_enum = NoteVisibility.PRIVATE
        
        # Validate project if provided
        project = None
        if project_id:
            project = Project.query.filter_by(
                id=project_id,
                company_id=g.user.company_id
            ).first()
            if not project:
                flash('Invalid project selected', 'error')
                return redirect(url_for('notes.create_note'))
        
        # Validate task if provided
        task = None
        if task_id:
            task = Task.query.filter_by(id=task_id).first()
            if not task or (project and task.project_id != project.id):
                flash('Invalid task selected', 'error')
                return redirect(url_for('notes.create_note'))
        
        # Create note
        note = Note(
            title=title,
            content=content,
            visibility=visibility_enum,
            folder=folder if folder else None,
            tags=tags if tags else None,
            company_id=g.user.company_id,
            created_by_id=g.user.id,
            project_id=project.id if project else None,
            task_id=task.id if task else None,
            is_pinned=is_pinned
        )
        
        # Generate slug before saving
        note.generate_slug()
        
        db.session.add(note)
        db.session.commit()
        
        flash('Note created successfully', 'success')
        return redirect(url_for('notes.view_note', slug=note.slug))
    
    # GET request - show form
    # Get folders for dropdown
    folders = NoteFolder.query.filter_by(
        company_id=g.user.company_id
    ).order_by(NoteFolder.path).all()
    
    # Get projects for dropdown
    projects = Project.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).order_by(Project.name).all()
    
    # Get task if specified in URL
    task_id = request.args.get('task_id')
    task = None
    if task_id:
        task = Task.query.filter_by(id=task_id).first()
    
    return render_template('note_editor.html',
                         folders=folders,
                         projects=projects,
                         task=task,
                         title='Create Note')


@notes_bp.route('/<slug>')
@login_required
@company_required
def view_note(slug):
    """View a note"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_view(g.user):
        abort(403)
    
    # Get linked notes
    outgoing_links = NoteLink.query.filter_by(
        source_note_id=note.id
    ).join(
        Note, NoteLink.target_note_id == Note.id
    ).filter(
        Note.is_archived == False
    ).all()
    
    incoming_links = NoteLink.query.filter_by(
        target_note_id=note.id
    ).join(
        Note, NoteLink.source_note_id == Note.id
    ).filter(
        Note.is_archived == False
    ).all()
    
    # Get linkable notes for the modal
    linkable_notes = Note.query.filter(
        Note.company_id == g.user.company_id,
        Note.id != note.id,
        Note.is_archived == False
    ).filter(
        or_(
            # User's private notes
            and_(Note.visibility == NoteVisibility.PRIVATE, Note.created_by_id == g.user.id),
            # Team notes
            and_(Note.visibility == NoteVisibility.TEAM, Note.created_by.has(team_id=g.user.team_id)),
            # Company notes
            Note.visibility == NoteVisibility.COMPANY
        )
    ).order_by(Note.title).all()
    
    return render_template('note_view.html',
                         note=note,
                         outgoing_links=outgoing_links,
                         incoming_links=incoming_links,
                         linkable_notes=linkable_notes,
                         title=note.title)


@notes_bp.route('/<slug>/mindmap')
@login_required
@company_required
def view_note_mindmap(slug):
    """View a note as a mind map"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_view(g.user):
        abort(403)
    
    return render_template('note_mindmap.html', note=note, title=f"{note.title} - Mind Map")


@notes_bp.route('/<slug>/edit', methods=['GET', 'POST'])
@login_required
@company_required
def edit_note(slug):
    """Edit an existing note"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_edit(g.user):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        visibility = request.form.get('visibility', 'Private')
        folder = request.form.get('folder', '').strip()
        tags = request.form.get('tags', '').strip()
        project_id = request.form.get('project_id')
        task_id = request.form.get('task_id')
        is_pinned = request.form.get('is_pinned') == '1'
        
        # Validate
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('notes.edit_note', slug=slug))
        
        if not content:
            flash('Content is required', 'error')
            return redirect(url_for('notes.edit_note', slug=slug))
        
        # Validate visibility
        try:
            visibility_enum = NoteVisibility[visibility.upper()]
        except KeyError:
            visibility_enum = NoteVisibility.PRIVATE
        
        # Validate project if provided
        project = None
        if project_id:
            project = Project.query.filter_by(
                id=project_id,
                company_id=g.user.company_id
            ).first()
            if not project:
                flash('Invalid project selected', 'error')
                return redirect(url_for('notes.edit_note', slug=slug))
        
        # Validate task if provided
        task = None
        if task_id:
            task = Task.query.filter_by(id=task_id).first()
            if not task or (project and task.project_id != project.id):
                flash('Invalid task selected', 'error')
                return redirect(url_for('notes.edit_note', slug=slug))
        
        # Update note
        note.title = title
        note.content = content
        note.visibility = visibility_enum
        note.folder = folder if folder else None
        note.tags = tags if tags else None
        note.project_id = project.id if project else None
        note.task_id = task.id if task else None
        note.is_pinned = is_pinned
        note.updated_at = datetime.now(timezone.utc)
        
        # Update slug if title changed
        note.generate_slug()
        
        db.session.commit()
        
        flash('Note updated successfully', 'success')
        return redirect(url_for('notes.view_note', slug=note.slug))
    
    # GET request - show form
    # Get folders for dropdown
    folders = NoteFolder.query.filter_by(
        company_id=g.user.company_id
    ).order_by(NoteFolder.path).all()
    
    # Get projects for dropdown
    projects = Project.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).order_by(Project.name).all()
    
    return render_template('note_editor.html',
                         note=note,
                         folders=folders,
                         projects=projects,
                         title=f'Edit {note.title}')


@notes_bp.route('/<slug>/delete', methods=['POST'])
@login_required
@company_required
def delete_note(slug):
    """Delete (archive) a note"""
    note = Note.query.filter_by(slug=slug, company_id=g.user.company_id).first_or_404()
    
    # Check permissions
    if not note.can_user_edit(g.user):
        abort(403)
    
    # Archive the note
    note.is_archived = True
    note.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Note deleted successfully', 'success')
    return redirect(url_for('notes.notes_list'))


@notes_bp.route('/folders')
@login_required
@company_required
def notes_folders():
    """Manage note folders"""
    # Get all folders
    folders = NoteFolder.query.filter_by(
        company_id=g.user.company_id
    ).order_by(NoteFolder.path).all()
    
    # Get note counts per folder
    folder_counts = {}
    folder_note_counts = db.session.query(
        Note.folder, db.func.count(Note.id)
    ).filter_by(
        company_id=g.user.company_id,
        is_archived=False
    ).filter(Note.folder.isnot(None)).group_by(Note.folder).all()
    
    for folder, count in folder_note_counts:
        folder_counts[folder] = count
    
    # Build folder tree
    folder_tree = {}
    for folder in folders:
        parts = folder.path.split('/')
        current = folder_tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    
    return render_template('notes_folders.html',
                         folders=folders,
                         folder_tree=folder_tree,
                         folder_counts=folder_counts,
                         title='Manage Folders')