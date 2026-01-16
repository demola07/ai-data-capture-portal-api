"""
Phone number validation and formatting utilities for Nigerian numbers
"""
import re
from typing import List, Tuple, Optional


def split_multiple_numbers(phone_string: str) -> List[str]:
    """
    Split a string that may contain multiple phone numbers.
    
    Handles separators: comma, slash, 'and', multiple spaces
    Examples:
        "08012345678, 09012345678" -> ["08012345678", "09012345678"]
        "08012345678/09012345678" -> ["08012345678", "09012345678"]
        "+2348012345678  09012345678" -> ["+2348012345678", "09012345678"]
    
    Args:
        phone_string: String potentially containing multiple phone numbers
        
    Returns:
        List of individual phone number strings
    """
    if not phone_string or not phone_string.strip():
        return []
    
    # Replace common separators with a standard delimiter
    normalized = phone_string
    normalized = re.sub(r'\s+and\s+', ',', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'[/]', ',', normalized)  # Replace / with comma
    normalized = re.sub(r'\s{2,}', ',', normalized)  # Multiple spaces -> comma
    
    # Split by comma and clean each part
    parts = [part.strip() for part in normalized.split(',')]
    
    # Filter out empty strings
    return [part for part in parts if part]


def clean_phone_number(phone: str) -> str:
    """
    Clean a phone number string by removing unwanted characters.
    
    Removes: spaces, dots, dashes, parentheses, text in parentheses
    Keeps: digits and leading +
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Cleaned phone number string
    """
    if not phone:
        return ""
    
    # Remove text in parentheses like "(incomplete number)"
    phone = re.sub(r'\([^)]*\)', '', phone)
    
    # Remove trailing letters (e.g., "08189008184o" -> "08189008184")
    phone = re.sub(r'[a-zA-Z]+$', '', phone)
    
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    return cleaned


def is_invalid_entry(phone: str) -> bool:
    """
    Check if a phone number entry should be filtered out.
    
    Filters out:
    - "Nil", "nil", "N/A", "None"
    - Empty strings
    - Strings with no digits
    
    Args:
        phone: Phone number string
        
    Returns:
        True if entry should be filtered out
    """
    if not phone or not phone.strip():
        return True
    
    phone_lower = phone.strip().lower()
    
    # Check for invalid keywords
    invalid_keywords = ['nil', 'n/a', 'none', 'null', 'na']
    if phone_lower in invalid_keywords:
        return True
    
    # Check if there are any digits at all
    if not re.search(r'\d', phone):
        return True
    
    return False


def format_nigerian_phone(phone: str) -> Optional[str]:
    """
    Format a Nigerian phone number to +234XXXXXXXXXX format.
    
    Accepts formats:
    - 08012345678 (starts with 0)
    - 8012345678 (without leading 0)
    - 2348012345678 (with country code, no +)
    - +2348012345678 (with + and country code)
    - +234 801 234 5678 (with spaces)
    - +234-801-234-5678 (with dashes)
    
    Args:
        phone: Phone number string in various formats
        
    Returns:
        Formatted phone number as +234XXXXXXXXXX or None if invalid
    """
    if not phone or is_invalid_entry(phone):
        return None
    
    # Clean the phone number
    cleaned = clean_phone_number(phone)
    
    if not cleaned:
        return None
    
    # Remove + if present for easier processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Handle different formats
    if cleaned.startswith('234'):
        # Already has country code: 234XXXXXXXXXX
        if len(cleaned) == 13:  # 234 + 10 digits
            return f"+{cleaned}"
        else:
            return None  # Invalid length
    
    elif cleaned.startswith('0'):
        # Local format with leading 0: 08012345678
        if len(cleaned) == 11:  # 0 + 10 digits
            return f"+234{cleaned[1:]}"  # Remove leading 0, add +234
        else:
            return None  # Invalid length (incomplete or too long)
    
    elif len(cleaned) == 10:
        # Local format without leading 0: 8012345678
        return f"+234{cleaned}"
    
    else:
        return None  # Invalid format


def validate_and_format_phones(phone_numbers: List[str]) -> Tuple[List[str], dict]:
    """
    Validate and format a list of Nigerian phone numbers with flexible parsing.
    
    Features:
    - Splits multiple numbers in single string (e.g., "0801234,0901234" -> 2 numbers)
    - Cleans formatting (spaces, dots, dashes, parentheses)
    - Filters out invalid entries (Nil, incomplete, non-numeric)
    - Returns only valid formatted numbers
    
    Args:
        phone_numbers: List of phone number strings (may contain multiple numbers each)
        
    Returns:
        Tuple of (valid_numbers, stats)
        - valid_numbers: List of unique formatted phone numbers (+234XXXXXXXXXX)
        - stats: Dict with processing statistics (total_input, total_output, filtered_count)
    """
    all_numbers = []
    
    # First pass: split and collect all individual numbers
    for phone_string in phone_numbers:
        if not phone_string:
            continue
        
        # Split if multiple numbers in one string
        individual_numbers = split_multiple_numbers(phone_string)
        all_numbers.extend(individual_numbers)
    
    # Second pass: format and validate each number
    valid_numbers = []
    filtered_count = 0
    
    for phone in all_numbers:
        formatted = format_nigerian_phone(phone)
        if formatted:
            valid_numbers.append(formatted)
        else:
            filtered_count += 1
    
    # Remove duplicates while preserving order
    seen = set()
    unique_valid_numbers = []
    for num in valid_numbers:
        if num not in seen:
            seen.add(num)
            unique_valid_numbers.append(num)
    
    stats = {
        "total_input": len(phone_numbers),
        "total_extracted": len(all_numbers),
        "total_valid": len(unique_valid_numbers),
        "filtered_count": filtered_count,
        "duplicate_count": len(valid_numbers) - len(unique_valid_numbers)
    }
    
    return unique_valid_numbers, stats


def is_valid_nigerian_phone(phone: str) -> bool:
    """
    Check if a phone number is a valid Nigerian number.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid, False otherwise
    """
    result = format_nigerian_phone(phone)
    return result is not None
