"""
Termii Email Provider implementation.
"""
import httpx
from typing import List, Optional
from datetime import datetime
import logging

from app.services.notifications.base import EmailProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class TermiiEmailProvider(EmailProvider):
    """Termii email provider implementation"""
    
    BASE_URL = "https://api.ng.termii.com/api/email/send"
    
    def __init__(self, api_key: str, sender_id: str, default_from_email: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.default_from_email = default_from_email
        self.provider_name = "termii"
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> NotificationResponse:
        """Send email via Termii API"""
        
        sender = from_email or self.default_from_email
        recipient = to[0] if len(to) == 1 else to[0]  # Send to one recipient at a time
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "email_from": sender,
                    "email_to": recipient,
                    "subject": subject,
                    "email_body": html_body or body,
                    "email_type": "html" if html_body else "plain"
                }
                
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
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
                        cost=ProviderCosts.TERMII_EMAIL,
                        sent_at=datetime.utcnow()
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
                        cost=0.0
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending email to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
