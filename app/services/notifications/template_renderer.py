"""
Template rendering utility for notification templates.
"""
import re
from typing import Dict, List, Optional
import json


class TemplateRenderer:
    """Renders templates with variable substitution"""
    
    @staticmethod
    def render(template: str, variables: Dict[str, str]) -> str:
        """
        Render a template by replacing {{variable}} placeholders with actual values.
        
        Args:
            template: Template string with {{variable}} placeholders
            variables: Dictionary of variable names and values
            
        Returns:
            Rendered template string
            
        Example:
            template = "Hello {{name}}, your session is on {{date}}"
            variables = {"name": "John", "date": "Dec 26"}
            result = "Hello John, your session is on Dec 26"
        """
        if not template:
            return ""
        
        rendered = template
        
        # Replace all {{variable}} with actual values
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    @staticmethod
    def extract_variables(template: str) -> List[str]:
        """
        Extract all variable names from a template.
        
        Args:
            template: Template string with {{variable}} placeholders
            
        Returns:
            List of variable names
            
        Example:
            template = "Hello {{name}}, your session is on {{date}}"
            result = ["name", "date"]
        """
        if not template:
            return []
        
        # Find all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, template)
        
        # Return unique variable names
        return list(set(matches))
    
    @staticmethod
    def validate_variables(template: str, provided_variables: Dict[str, str]) -> tuple[bool, List[str]]:
        """
        Validate that all required variables are provided.
        
        Args:
            template: Template string
            provided_variables: Variables provided by user
            
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        required_variables = TemplateRenderer.extract_variables(template)
        missing = [var for var in required_variables if var not in provided_variables]
        
        return (len(missing) == 0, missing)
    
    @staticmethod
    def get_standard_variables() -> Dict[str, str]:
        """
        Get standard variables that are always available.
        
        Returns:
            Dictionary of standard variable names and descriptions
        """
        return {
            "recipient_name": "Name of the recipient",
            "recipient_email": "Email of the recipient",
            "recipient_phone": "Phone number of the recipient",
            "current_date": "Current date",
            "current_year": "Current year",
            "organization_name": "YMR Counselling Unit",
            "support_email": "ymrcounsellingfollowup@gmail.com",
            "support_phone": "+234 816 249 5328",
            "community_group_link": "https://t.me/ymr_new_army_2025"
        }

