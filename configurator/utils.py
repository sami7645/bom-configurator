from decimal import Decimal
import re


def format_artikelnummer(artikelnummer):
    """Format article number by removing .0 suffix if present"""
    if not artikelnummer:
        return ''
    artikelnummer = str(artikelnummer).strip()
    if artikelnummer.endswith('.0'):
        artikelnummer = artikelnummer[:-2]
    return artikelnummer


def calculate_formula(formula, context):
    """Safely calculate formula with given context"""
    if not formula or formula.strip() == '':
        return None

    try:
        safe_formula = formula.strip()
        if safe_formula.startswith('='):
            safe_formula = safe_formula[1:]

        sorted_keys = sorted(context.keys(), key=len, reverse=True)
        for key in sorted_keys:
            value = context[key]
            pattern = r'\b' + re.escape(key) + r'\b'
            safe_formula = re.sub(pattern, str(value), safe_formula)

        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in safe_formula):
            return None

        result = eval(safe_formula)
        return Decimal(str(result))
    except Exception as exc:
        print(f"Formula calculation error: {exc}")
        return None


def check_compatibility(compatibility_field, hvb_size, sonden_durchmesser, check_type='either'):
    """Check if an item is compatible with the selected HVB size and probe diameter."""
    if not compatibility_field or not compatibility_field.strip():
        return True

    hvb_formatted = f"DA {hvb_size}" if hvb_size else ''
    sonden_formatted = f"DA {sonden_durchmesser}" if sonden_durchmesser else ''
    compatible_values = [value.strip() for value in compatibility_field.split('|')]

    if check_type == 'hvb':
        return hvb_formatted in compatible_values
    if check_type == 'sonden':
        return sonden_formatted in compatible_values
    return hvb_formatted in compatible_values or sonden_formatted in compatible_values

