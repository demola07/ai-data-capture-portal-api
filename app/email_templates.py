"""
Email template constants and mappings.

This file maps template keys (used by frontend) to actual Termii template IDs.
Update the template IDs here after creating templates in Termii dashboard.
"""

class EmailTemplates:
    """Email template key to Termii template ID mappings"""
    
    # Template IDs - Update these with actual IDs from Termii dashboard
    WELCOME = "dde43602-22f4-4761-b4e3-4fc350b45038"  # New convert welcome email
    
    # Template key to ID mapping
    TEMPLATES = {
        "welcome": WELCOME,
    }
    
    @classmethod
    def get_template_id(cls, template_key: str) -> str:
        """
        Get Termii template ID from template key.
        
        Args:
            template_key: Template key (e.g., "welcome", "password_reset")
            
        Returns:
            Termii template ID
            
        Raises:
            ValueError: If template key not found
        """
        template_id = cls.TEMPLATES.get(template_key.lower())
        
        if not template_id:
            available_keys = ", ".join(cls.TEMPLATES.keys())
            raise ValueError(
                f"Template key '{template_key}' not found. "
                f"Available templates: {available_keys}"
            )
        
        return template_id
    
    @classmethod
    def get_available_templates(cls) -> dict:
        """Get all available template keys and their IDs"""
        return cls.TEMPLATES.copy()
