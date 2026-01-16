"""
Phone number validation and formatting utilities for Nigerian numbers
"""
import re
from typing import List, Tuple


def format_nigerian_phone(phone: str) -> str:
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
        Formatted phone number as +234XXXXXXXXXX
        
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number cannot be empty")
    
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # Remove + if present for easier processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Handle different formats
    if cleaned.startswith('234'):
        # Already has country code: 234XXXXXXXXXX
        if len(cleaned) == 13:  # 234 + 10 digits
            return f"+{cleaned}"
        else:
            raise ValueError(f"Invalid Nigerian phone number length: {phone}")
    
    elif cleaned.startswith('0'):
        # Local format with leading 0: 08012345678
        if len(cleaned) == 11:  # 0 + 10 digits
            return f"+234{cleaned[1:]}"  # Remove leading 0, add +234
        else:
            raise ValueError(f"Invalid Nigerian phone number length: {phone}")
    
    elif len(cleaned) == 10:
        # Local format without leading 0: 8012345678
        return f"+234{cleaned}"
    
    else:
        raise ValueError(f"Invalid Nigerian phone number format: {phone}")


def validate_and_format_phones(phone_numbers: List[str]) -> Tuple[List[str], List[dict]]:
    """
    Validate and format a list of Nigerian phone numbers.
    
    Args:
        phone_numbers: List of phone numbers in various formats
        
    Returns:
        Tuple of (valid_numbers, errors)
        - valid_numbers: List of formatted phone numbers (+234XXXXXXXXXX)
        - errors: List of dicts with 'phone' and 'error' keys for invalid numbers
    """
    valid_numbers = []
    errors = []
    
    for phone in phone_numbers:
        try:
            formatted = format_nigerian_phone(phone)
            valid_numbers.append(formatted)
        except ValueError as e:
            errors.append({
                "phone": phone,
                "error": str(e)
            })
    
    return valid_numbers, errors


def is_valid_nigerian_phone(phone: str) -> bool:
    """
    Check if a phone number is a valid Nigerian number.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        format_nigerian_phone(phone)
        return True
    except ValueError:
        return False
