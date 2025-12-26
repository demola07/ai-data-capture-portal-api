"""
Termii Email Provider implementation with template support.
"""
import httpx
import json
from typing import List, Optional, Dict
from datetime import datetime
import logging

from app.services.notifications.base import EmailProvider, NotificationResponse
from app.constants import NotificationStatus

logger = logging.getLogger(__name__)


class TermiiEmailProvider(EmailProvider):
    """Termii email provider with template support"""
    
    BASE_URL = "https://api.termii.com/api/templates/send-email"
    
    def __init__(self, api_key: str, email_configuration_id: str):
        self.api_key = api_key
        self.email_configuration_id = email_configuration_id
        self.provider_name = "termii"
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        template_id: str,
        variables: Dict[str, str],
        from_email: Optional[str] = None
    ) -> NotificationResponse:
        """
        Send templated email via Termii API.
        
        Args:
            to: List of email addresses (only first one is used per call)
            subject: Email subject line
            template_id: Termii template ID from dashboard
            variables: Key-value pairs for template variables
            from_email: Not used (configured in Termii dashboard)
        """
        
        recipient = to[0] if to else None
        if not recipient:
            return NotificationResponse(
                success=False,
                recipient="",
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="No recipient provided",
                cost="0"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "email": recipient,
                    "subject": subject,
                    "email_configuration_id": self.email_configuration_id,
                    "template_id": template_id,
                    "variables": variables
                }
                
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("code") == "ok":
                    return NotificationResponse(
                        success=True,
                        recipient=recipient,
                        message_id=response_data.get("message_id"),
                        provider=self.provider_name,
                        status=NotificationStatus.SENT,
                        cost=str(response_data.get("balance", "0")),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data),
                        metadata=json.dumps({"template_id": template_id, "variables": variables})
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Termii error sending to {recipient}: {error_message}")
                    
                    return NotificationResponse(
                        success=False,
                        recipient=recipient,
                        provider=self.provider_name,
                        status=NotificationStatus.FAILED,
                        error=error_message,
                        cost="0"
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending email to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost="0"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost="0"
            )
