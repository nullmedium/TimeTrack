"""
Template filters and utilities for Jinja2
"""

from utils.currency import format_money, get_currency_symbol


def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('format_money')
    def format_money_filter(amount, currency_code):
        """Format money amount with currency"""
        return format_money(amount, currency_code)
    
    @app.template_filter('currency_symbol')
    def currency_symbol_filter(currency_code):
        """Get currency symbol from code"""
        return get_currency_symbol(currency_code)
    
    # Make functions available in all templates
    app.jinja_env.globals.update(
        format_money=format_money,
        get_currency_symbol=get_currency_symbol
    )