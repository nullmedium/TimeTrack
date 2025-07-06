"""Password validation utilities for TimeTrack"""
import re

class PasswordValidator:
    """Password strength validator with configurable rules"""
    
    def __init__(self):
        self.min_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_numbers = True
        self.require_special_chars = True
        self.special_chars = r'!@#$%^&*()_+\-=\[\]{}|;:,.<>?'
        
    def validate(self, password):
        """
        Validate a password against the configured rules.
        Returns a tuple (is_valid, list_of_errors)
        """
        errors = []
        
        # Check minimum length
        if len(password) < self.min_length:
            errors.append(f'Password must be at least {self.min_length} characters long')
        
        # Check for uppercase letter
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter')
        
        # Check for lowercase letter
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter')
        
        # Check for number
        if self.require_numbers and not re.search(r'\d', password):
            errors.append('Password must contain at least one number')
        
        # Check for special character
        if self.require_special_chars and not re.search(f'[{re.escape(self.special_chars)}]', password):
            errors.append('Password must contain at least one special character')
        
        return len(errors) == 0, errors
    
    def get_strength_score(self, password):
        """
        Calculate a strength score for the password (0-100).
        This matches the JavaScript implementation.
        """
        score = 0
        
        # Base scoring
        if len(password) >= self.min_length:
            score += 20
        
        if re.search(r'[A-Z]', password):
            score += 20
            
        if re.search(r'[a-z]', password):
            score += 20
            
        if re.search(r'\d', password):
            score += 20
            
        if re.search(f'[{re.escape(self.special_chars)}]', password):
            score += 20
        
        # Bonus points for extra length
        if len(password) >= 12:
            score = min(100, score + 10)
        if len(password) >= 16:
            score = min(100, score + 10)
        
        return score
    
    def get_requirements_text(self):
        """Get a user-friendly text describing password requirements"""
        requirements = []
        requirements.append(f'At least {self.min_length} characters')
        
        if self.require_uppercase:
            requirements.append('One uppercase letter')
        if self.require_lowercase:
            requirements.append('One lowercase letter')
        if self.require_numbers:
            requirements.append('One number')
        if self.require_special_chars:
            requirements.append('One special character (!@#$%^&*()_+-=[]{}|;:,.<>?)')
        
        return requirements