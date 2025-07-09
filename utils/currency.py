"""
Currency utilities for TimeTrack
"""

# Common currency symbols mapping
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CNY': '¥',
    'CHF': 'CHF',
    'CAD': 'C$',
    'AUD': 'A$',
    'NZD': 'NZ$',
    'SEK': 'kr',
    'NOK': 'kr',
    'DKK': 'kr',
    'PLN': 'zł',
    'CZK': 'Kč',
    'HUF': 'Ft',
    'RON': 'lei',
    'BGN': 'лв',
    'HRK': 'kn',
    'RUB': '₽',
    'TRY': '₺',
    'BRL': 'R$',
    'MXN': '$',
    'ARS': '$',
    'CLP': '$',
    'COP': '$',
    'PEN': 'S/',
    'UYU': '$U',
    'INR': '₹',
    'PKR': '₨',
    'BDT': '৳',
    'LKR': '₨',
    'THB': '฿',
    'VND': '₫',
    'KRW': '₩',
    'MYR': 'RM',
    'SGD': 'S$',
    'IDR': 'Rp',
    'PHP': '₱',
    'ZAR': 'R',
    'NGN': '₦',
    'KES': 'KSh',
    'EGP': 'E£',
    'AED': 'د.إ',
    'SAR': '﷼',
    'QAR': '﷼',
    'ILS': '₪',
}

# Currency display names
CURRENCY_NAMES = {
    'USD': 'US Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'JPY': 'Japanese Yen',
    'CNY': 'Chinese Yuan',
    'CHF': 'Swiss Franc',
    'CAD': 'Canadian Dollar',
    'AUD': 'Australian Dollar',
    'NZD': 'New Zealand Dollar',
    'SEK': 'Swedish Krona',
    'NOK': 'Norwegian Krone',
    'DKK': 'Danish Krone',
    'PLN': 'Polish Złoty',
    'CZK': 'Czech Koruna',
    'HUF': 'Hungarian Forint',
    'RON': 'Romanian Leu',
    'BGN': 'Bulgarian Lev',
    'HRK': 'Croatian Kuna',
    'RUB': 'Russian Ruble',
    'TRY': 'Turkish Lira',
    'BRL': 'Brazilian Real',
    'MXN': 'Mexican Peso',
    'ARS': 'Argentine Peso',
    'CLP': 'Chilean Peso',
    'COP': 'Colombian Peso',
    'PEN': 'Peruvian Sol',
    'UYU': 'Uruguayan Peso',
    'INR': 'Indian Rupee',
    'PKR': 'Pakistani Rupee',
    'BDT': 'Bangladeshi Taka',
    'LKR': 'Sri Lankan Rupee',
    'THB': 'Thai Baht',
    'VND': 'Vietnamese Dong',
    'KRW': 'South Korean Won',
    'MYR': 'Malaysian Ringgit',
    'SGD': 'Singapore Dollar',
    'IDR': 'Indonesian Rupiah',
    'PHP': 'Philippine Peso',
    'ZAR': 'South African Rand',
    'NGN': 'Nigerian Naira',
    'KES': 'Kenyan Shilling',
    'EGP': 'Egyptian Pound',
    'AED': 'UAE Dirham',
    'SAR': 'Saudi Riyal',
    'QAR': 'Qatari Riyal',
    'ILS': 'Israeli Shekel',
}

# Common currencies for dropdown
COMMON_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CNY', 'CHF',
    'SEK', 'NOK', 'DKK', 'INR', 'BRL', 'MXN', 'SGD', 'HKD'
]


def get_currency_symbol(currency_code):
    """Get the symbol for a currency code"""
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)


def get_currency_name(currency_code):
    """Get the full name for a currency code"""
    return CURRENCY_NAMES.get(currency_code.upper(), currency_code)


def format_money(amount, currency_code, include_code=False):
    """Format a money amount with currency symbol"""
    if amount is None:
        return ''
    
    symbol = get_currency_symbol(currency_code)
    
    # Format with 2 decimal places
    formatted = f"{amount:,.2f}"
    
    # Some currencies put symbol after (e.g., Swedish krona)
    if currency_code in ['SEK', 'NOK', 'DKK', 'CZK', 'PLN']:
        result = f"{formatted} {symbol}"
    else:
        result = f"{symbol}{formatted}"
    
    if include_code and currency_code not in CURRENCY_SYMBOLS:
        result = f"{currency_code} {formatted}"
    
    return result


def get_currency_choices():
    """Get currency choices for forms"""
    choices = []
    
    # Add common currencies first
    for code in COMMON_CURRENCIES:
        name = get_currency_name(code)
        symbol = get_currency_symbol(code)
        label = f"{code} - {name} ({symbol})"
        choices.append((code, label))
    
    # Add separator
    choices.append(('---', '--- All Currencies ---'))
    
    # Add all other currencies
    for code, name in sorted(CURRENCY_NAMES.items()):
        if code not in COMMON_CURRENCIES:
            symbol = get_currency_symbol(code)
            label = f"{code} - {name} ({symbol})"
            choices.append((code, label))
    
    return choices