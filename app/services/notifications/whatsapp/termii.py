"""
Termii WhatsApp Provider implementation.
"""
import httpx
from typing import List, Optional
from datetime import datetime
import logging

from app.services.notifications.base import WhatsAppProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class TermiiWhatsAppProvider(WhatsAppProvider):
    """Termii WhatsApp provider implementation"""
    
    BASE_URL = "https://api.ng.termii.com/api/whatsapp/send"
    
    def __init__(self, api_key: str, sender_id: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.provider_name = "termii"
    
    async def send_whatsapp(
        self,
        to: List[str],
        message: str,
        template_id: Optional[str] = None
    ) -> NotificationResponse:
        """Send WhatsApp message via Termii API"""
        
        recipient = to[0] if len(to) == 1 else to[0]  # Send to one recipient at a time
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": recipient,
                    "from": self.sender_id,
                    "message": message,
                }
                
                if template_id:
                    payload["template_id"] = template_id
                
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
                        cost=ProviderCosts.TERMII_WHATSAPP,
                        sent_at=datetime.utcnow()
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Termii WhatsApp error sending to {recipient}: {error_message}")
                    
                    return NotificationResponse(
                        success=False,
                        recipient=recipient,
                        provider=self.provider_name,
                        status=NotificationStatus.FAILED,
                        error=error_message,
                        cost=0.0
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending WhatsApp to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
