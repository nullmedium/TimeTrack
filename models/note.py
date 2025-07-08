"""
Note models for markdown-based documentation and knowledge management.
Migrated from models_old.py to maintain consistency with the new modular structure.
"""

import enum
import re
from datetime import datetime, timedelta

from sqlalchemy import UniqueConstraint

from . import db
from .enums import Role


class NoteVisibility(enum.Enum):
    """Note sharing visibility levels"""
    PRIVATE = "Private"
    TEAM = "Team"
    COMPANY = "Company"


class Note(db.Model):
    """Markdown notes with sharing capabilities"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown content
    slug = db.Column(db.String(100), nullable=False)  # URL-friendly identifier
    
    # Visibility and sharing
    visibility = db.Column(db.Enum(NoteVisibility), nullable=False, default=NoteVisibility.PRIVATE)
    
    # Folder organization
    folder = db.Column(db.String(100), nullable=True)  # Folder path like "Work/Projects" or "Personal"
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Associations
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Optional associations
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # For team-specific notes
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)  # Link to project
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)  # Link to task
    
    # Tags for organization
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Pin important notes
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Soft delete
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='notes')
    company = db.relationship('Company', backref='notes')
    team = db.relationship('Team', backref='notes')
    project = db.relationship('Project', backref='notes')
    task = db.relationship('Task', backref='notes')
    
    # Unique constraint on slug per company
    __table_args__ = (db.UniqueConstraint('company_id', 'slug', name='uq_note_slug_per_company'),)
    
    def __repr__(self):
        return f'<Note {self.title}>'
    
    def generate_slug(self):
        """Generate URL-friendly slug from title and set it on the model"""
        import re
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', self.title.lower())
        # Replace spaces with hyphens
        slug = re.sub(r'[-\s]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Ensure uniqueness within company
        base_slug = slug
        counter = 1
        while Note.query.filter_by(company_id=self.company_id, slug=slug).filter(Note.id != self.id).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        self.slug = slug
        return slug
    
    def can_user_view(self, user):
        """Check if user can view this note"""
        # Creator can always view
        if user.id == self.created_by_id:
            return True
        
        # Check company match
        if user.company_id != self.company_id:
            return False
        
        # Check visibility
        if self.visibility == NoteVisibility.COMPANY:
            return True
        elif self.visibility == NoteVisibility.TEAM:
            # Check if user is in the same team
            if self.team_id and user.team_id == self.team_id:
                return True
            # Admins can view all team notes
            if user.role in [Role.ADMIN, Role.SYSTEM_ADMIN]:
                return True
        
        return False
    
    def can_user_edit(self, user):
        """Check if user can edit this note"""
        # Creator can always edit
        if user.id == self.created_by_id:
            return True
        
        # Admins can edit company notes
        if user.role in [Role.ADMIN, Role.SYSTEM_ADMIN] and user.company_id == self.company_id:
            return True
        
        return False
    
    def get_tags_list(self):
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags_list(self, tags_list):
        """Set tags from a list"""
        self.tags = ','.join(tags_list) if tags_list else None
    
    def get_preview(self, length=200):
        """Get a plain text preview of the note content"""
        # Strip markdown formatting for preview
        import re
        from frontmatter_utils import parse_frontmatter
        
        # Extract body content without frontmatter
        _, body = parse_frontmatter(self.content)
        text = body
        
        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # Remove emphasis
        text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Clean up whitespace
        text = ' '.join(text.split())
        
        if len(text) > length:
            return text[:length] + '...'
        return text
    
    def render_html(self):
        """Render markdown content to HTML"""
        try:
            import markdown
            from frontmatter_utils import parse_frontmatter
            # Extract body content without frontmatter
            _, body = parse_frontmatter(self.content)
            # Use extensions for better markdown support
            html = markdown.markdown(body, extensions=['extra', 'codehilite', 'toc'])
            return html
        except ImportError:
            # Fallback if markdown not installed
            return f'<pre>{self.content}</pre>'
    
    def get_frontmatter(self):
        """Get frontmatter metadata from content"""
        from frontmatter_utils import parse_frontmatter
        metadata, _ = parse_frontmatter(self.content)
        return metadata
    
    def update_frontmatter(self):
        """Update content with current metadata as frontmatter"""
        from frontmatter_utils import update_frontmatter
        metadata = {
            'title': self.title,
            'visibility': self.visibility.value.lower(),
            'folder': self.folder,
            'tags': self.get_tags_list() if self.tags else None,
            'project': self.project.code if self.project else None,
            'task_id': self.task_id,
            'pinned': self.is_pinned if self.is_pinned else None,
            'created': self.created_at.isoformat() if self.created_at else None,
            'updated': self.updated_at.isoformat() if self.updated_at else None,
            'author': self.created_by.username if self.created_by else None
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        self.content = update_frontmatter(self.content, metadata)
    
    def sync_from_frontmatter(self):
        """Update model fields from frontmatter in content"""
        from frontmatter_utils import parse_frontmatter
        metadata, _ = parse_frontmatter(self.content)
        
        if metadata:
            # Update fields from frontmatter
            if 'title' in metadata:
                self.title = metadata['title']
            if 'visibility' in metadata:
                try:
                    self.visibility = NoteVisibility[metadata['visibility'].upper()]
                except KeyError:
                    pass
            if 'folder' in metadata:
                self.folder = metadata['folder']
            if 'tags' in metadata:
                if isinstance(metadata['tags'], list):
                    self.set_tags_list(metadata['tags'])
                elif isinstance(metadata['tags'], str):
                    self.tags = metadata['tags']
            if 'pinned' in metadata:
                self.is_pinned = bool(metadata['pinned'])
    
    def create_share_link(self, expires_in_days=None, password=None, max_views=None, created_by=None):
        """Create a public share link for this note"""
        from .note_share import NoteShare
        from flask import g
        
        share = NoteShare(
            note_id=self.id,
            created_by_id=created_by.id if created_by else g.user.id
        )
        
        # Set expiration
        if expires_in_days:
            share.expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        # Set password
        if password:
            share.set_password(password)
        
        # Set view limit
        if max_views:
            share.max_views = max_views
        
        db.session.add(share)
        return share
    
    def get_active_shares(self):
        """Get all active share links for this note"""
        return [s for s in self.shares if s.is_valid()]
    
    def get_all_shares(self):
        """Get all share links for this note"""
        from models.note_share import NoteShare
        return self.shares.order_by(NoteShare.created_at.desc()).all()
    
    def has_active_shares(self):
        """Check if this note has any active share links"""
        return any(s.is_valid() for s in self.shares)


class NoteLink(db.Model):
    """Links between notes for creating relationships"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Source and target notes with cascade deletion
    source_note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    target_note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    
    # Link metadata
    link_type = db.Column(db.String(50), default='related')  # related, parent, child, etc.
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships with cascade deletion
    source_note = db.relationship('Note', foreign_keys=[source_note_id], 
                                backref=db.backref('outgoing_links', cascade='all, delete-orphan'))
    target_note = db.relationship('Note', foreign_keys=[target_note_id], 
                                backref=db.backref('incoming_links', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Unique constraint to prevent duplicate links
    __table_args__ = (db.UniqueConstraint('source_note_id', 'target_note_id', name='uq_note_link'),)
    
    def __repr__(self):
        return f'<NoteLink {self.source_note_id} -> {self.target_note_id}>'


class NoteFolder(db.Model):
    """Represents a folder for organizing notes"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Folder properties
    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(500), nullable=False)  # Full path like "Work/Projects/Q1"
    parent_path = db.Column(db.String(500), nullable=True)  # Parent folder path
    description = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    company = db.relationship('Company', foreign_keys=[company_id])
    
    # Unique constraint to prevent duplicate paths within a company
    __table_args__ = (db.UniqueConstraint('path', 'company_id', name='uq_folder_path_company'),)
    
    def __repr__(self):
        return f'<NoteFolder {self.path}>'