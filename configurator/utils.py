from decimal import Decimal
import re


def parse_allowed_hvb_sizes(erlaubte_hvb):
    """
    Parse allowed HVB sizes from erlaubte_hvb field.
    Extracts only DA values (DA 63, DA 75, etc.) and ignores other text.
    
    Examples:
        "DA 63" -> ["63"]
        "DA 63|DA 75|DA 90" -> ["63", "75", "90"]
        "Max 10 Sonden; HVB ≤ DA 110" -> ["110"]
        "DA 63|DA 75|DA 90|DA 110|DA 125" -> ["63", "75", "90", "110", "125"]
    
    Args:
        erlaubte_hvb: String containing allowed HVB values
        
    Returns:
        List of HVB sizes as strings (without "DA" prefix)
    """
    if not erlaubte_hvb or not erlaubte_hvb.strip():
        return []
    
    # Find all patterns like "DA 63", "DA 75", etc.
    # Pattern: DA followed by space and 2-3 digits
    pattern = r'DA\s+(\d{2,3})'
    matches = re.findall(pattern, str(erlaubte_hvb))
    
    # Remove duplicates and sort numerically
    unique_sizes = list(set(matches))
    # Sort as integers for proper numerical order
    unique_sizes.sort(key=lambda x: int(x))
    
    return unique_sizes


def extract_numeric_range_for_sorting(text):
    """
    Extract numeric range from text for sorting purposes.
    Looks for patterns like "2-12", "35-70", "5-42", etc.
    Returns a tuple (first_number, second_number) for sorting.
    If no range found, returns (999999, 999999) to sort to end.
    
    Examples:
        "K-DFM 2-12" -> (2, 12)
        "K-DFM 35-70" -> (35, 70)
        "HC VTR 20" -> (20, 20)
        "No numbers" -> (999999, 999999)
    """
    if not text:
        return (999999, 999999)
    
    # Look for pattern: number-number (e.g., "2-12", "35-70")
    range_match = re.search(r'(\d+)\s*-\s*(\d+)', str(text))
    if range_match:
        first = int(range_match.group(1))
        second = int(range_match.group(2))
        return (first, second)
    
    # Look for single number (e.g., "HC VTR 20")
    single_match = re.search(r'(\d+)', str(text))
    if single_match:
        num = int(single_match.group(1))
        return (num, num)
    
    # No numbers found, sort to end
    return (999999, 999999)


def sort_by_numeric_range(items):
    """
    Sort a list of strings by extracting numeric ranges from them.
    Items with numeric ranges are sorted by the second number (after dash), then first.
    Items without numbers are sorted alphabetically at the end.
    
    Args:
        items: List of strings to sort
        
    Returns:
        Sorted list
    """
    def sort_key(item):
        numeric_range = extract_numeric_range_for_sorting(item)
        # Return tuple: (second_num, first_num, original_text)
        # Sort by second number (after dash) first, then first number
        # This ensures items with same second number are sorted by first number
        return (numeric_range[1], numeric_range[0], str(item).lower())
    
    return sorted(items, key=sort_key)


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
        
        # Many CSV formulas contain human-readable comments after the actual
        # expression (e.g. "sondenanzahl*2 (if probe is 32 mm ...)").
        # We only want to evaluate the leading numeric expression and ignore
        # any trailing descriptive text.
        # Find the first opening parenthesis and check if it's balanced
        paren_pos = safe_formula.find('(')
        if paren_pos >= 0:
            # Check if parentheses are balanced from this point
            paren_count = 0
            balanced = True
            for i in range(paren_pos, len(safe_formula)):
                if safe_formula[i] == '(':
                    paren_count += 1
                elif safe_formula[i] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        # Found matching closing paren, include the full expression
                        break
            else:
                # No matching closing paren found - truncate before the opening paren
                if paren_count > 0:
                    safe_formula = safe_formula[:paren_pos].strip()
        
        # Extract only the numeric expression part (numbers, operators, spaces, balanced parens)
        # Match from start: numbers, operators, spaces, and balanced parentheses
        match = re.match(r'[0-9+\-*/().\s]+', safe_formula)
        if not match:
            return None

        safe_formula = match.group(0).strip()
        if not safe_formula:
            return None

        # Verify parentheses are balanced before eval
        if safe_formula.count('(') != safe_formula.count(')'):
            # Unbalanced parentheses - extract only the part before the first unclosed paren
            paren_pos = safe_formula.find('(')
            if paren_pos >= 0:
                safe_formula = safe_formula[:paren_pos].strip()
            if not safe_formula:
                return None

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

    # Strip 'mm' suffix if present from both HVB and probe diameter
    hvb_clean = str(hvb_size).strip()
    if hvb_clean.lower().endswith('mm'):
        hvb_clean = hvb_clean[:-2].strip()
    
    sonden_clean = str(sonden_durchmesser).strip()
    if sonden_clean.lower().endswith('mm'):
        sonden_clean = sonden_clean[:-2].strip()

    hvb_formatted = f"DA {hvb_clean}" if hvb_clean else ''
    sonden_formatted = f"DA {sonden_clean}" if sonden_clean else ''
    compatible_values = [value.strip() for value in compatibility_field.split('|')]

    if check_type == 'hvb':
        return hvb_formatted in compatible_values
    if check_type == 'sonden':
        return sonden_formatted in compatible_values
    return hvb_formatted in compatible_values or sonden_formatted in compatible_values

