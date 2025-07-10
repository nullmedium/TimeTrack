"""
Security headers middleware for Flask.
Add this to ensure secure form submission and prevent security warnings.
"""

from flask import request

def add_security_headers(response):
    """Add security headers to all responses."""
    
    # Force HTTPS for all resources
    if request.is_secure or not request.app.debug:
        # Strict Transport Security - force HTTPS for 1 year
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy - allow forms to submit only over HTTPS
        # Adjust this based on your needs
        csp = (
            "default-src 'self' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "form-action 'self' https:; "  # Forms can only submit to HTTPS
            "upgrade-insecure-requests; "  # Upgrade any HTTP requests to HTTPS
        )
        response.headers['Content-Security-Policy'] = csp
    
    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


def init_security(app):
    """Initialize security headers for the Flask app."""
    app.after_request(add_security_headers)