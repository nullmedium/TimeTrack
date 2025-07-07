"""
Repository pattern for common database operations
"""

from flask import g
from models import db


class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, model):
        self.model = model
    
    def get_by_id(self, id):
        """Get entity by ID"""
        return self.model.query.get(id)
    
    def get_by_company(self, company_id=None):
        """Get all entities for a company"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return []
        
        return self.model.query.filter_by(company_id=company_id).all()
    
    def get_by_company_ordered(self, company_id=None, order_by=None):
        """Get all entities for a company with ordering"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return []
        
        query = self.model.query.filter_by(company_id=company_id)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        return query.all()
    
    def exists_by_name_in_company(self, name, company_id=None, exclude_id=None):
        """Check if entity with name exists in company"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        query = self.model.query.filter_by(name=name, company_id=company_id)
        
        if exclude_id is not None:
            query = query.filter(self.model.id != exclude_id)
        
        return query.first() is not None
    
    def create(self, **kwargs):
        """Create new entity"""
        entity = self.model(**kwargs)
        db.session.add(entity)
        return entity
    
    def update(self, entity, **kwargs):
        """Update entity with given attributes"""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return entity
    
    def delete(self, entity):
        """Delete entity"""
        db.session.delete(entity)
    
    def save(self):
        """Commit changes to database"""
        db.session.commit()
    
    def rollback(self):
        """Rollback database changes"""
        db.session.rollback()


class CompanyScopedRepository(BaseRepository):
    """Repository for entities scoped to a company"""
    
    def get_by_id_and_company(self, id, company_id=None):
        """Get entity by ID, ensuring it belongs to the company"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return None
        
        return self.model.query.filter_by(id=id, company_id=company_id).first()
    
    def get_active_by_company(self, company_id=None):
        """Get active entities for a company"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return []
        
        # Assumes model has is_active field
        if hasattr(self.model, 'is_active'):
            return self.model.query.filter_by(
                company_id=company_id, 
                is_active=True
            ).all()
        
        return self.get_by_company(company_id)
    
    def count_by_company(self, company_id=None):
        """Count entities for a company"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return 0
        
        return self.model.query.filter_by(company_id=company_id).count()


# Specific repositories for common entities

class UserRepository(CompanyScopedRepository):
    """Repository for User operations"""
    
    def __init__(self):
        from models import User
        super().__init__(User)
    
    def get_by_username_and_company(self, username, company_id):
        """Get user by username within a company"""
        return self.model.query.filter_by(
            username=username, 
            company_id=company_id
        ).first()
    
    def get_by_email(self, email):
        """Get user by email (globally unique)"""
        return self.model.query.filter_by(email=email).first()


class TeamRepository(CompanyScopedRepository):
    """Repository for Team operations"""
    
    def __init__(self):
        from models import Team
        super().__init__(Team)
    
    def get_with_member_count(self, company_id=None):
        """Get teams with member count"""
        if company_id is None and hasattr(g, 'user') and g.user:
            company_id = g.user.company_id
        
        if company_id is None:
            return []
        
        # This would need a more complex query with joins
        teams = self.get_by_company(company_id)
        for team in teams:
            team.member_count = len(team.users)
        return teams


class ProjectRepository(CompanyScopedRepository):
    """Repository for Project operations"""
    
    def __init__(self):
        from models import Project
        super().__init__(Project)
    
    def get_by_code_and_company(self, code, company_id):
        """Get project by code within a company"""
        return self.model.query.filter_by(
            code=code, 
            company_id=company_id
        ).first()
    
    def get_accessible_by_user(self, user):
        """Get projects accessible by a user"""
        if not user:
            return []
        
        # Admin/Supervisor can see all company projects
        if user.role.value in ['Administrator', 'Supervisor', 'System Administrator']:
            return self.get_by_company(user.company_id)
        
        # Team members see team projects + unassigned projects
        from models import Project
        return Project.query.filter(
            Project.company_id == user.company_id,
            db.or_(
                Project.team_id == user.team_id,
                Project.team_id.is_(None)
            )
        ).all()