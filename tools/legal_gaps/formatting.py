"""Human workbook labels; identifiers and numeric source values remain intact."""
import re


def heading(value):
    words = value.replace('_', ' ').split()
    return ' '.join(w.upper() if w.lower() in ('usd', 'id', 'aru', 'bst', 'ppa', 'dta') else w.capitalize() for w in words)


def cell(value, column):
    if isinstance(value, str) and column.lower() in ('measure', 'field', 'metric', 'component') and re.fullmatch(r'[a-z][a-z0-9_]+', value) and '_' in value:
        return heading(value)
    return value
