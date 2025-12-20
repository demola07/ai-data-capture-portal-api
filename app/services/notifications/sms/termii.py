"""
Termii SMS Provider implementation.
"""
import httpx
from typing import List
from datetime import datetime
import logging

from app.services.notifications.base import SMSProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class TermiiSMSProvider(SMSProvider):
    """Termii SMS provider implementation"""
    
    BASE_URL = "https://v3.api.termii.com"
    
    def __init__(self, api_key: str, sender_id: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.provider_name = "termii"
    
    async def send_sms(
        self,
        to: List[str],
        message: str
    ) -> NotificationResponse:
        """Send SMS via Termii API"""
        
        recipient = to[0] if len(to) == 1 else to[0]  # Send to one recipient at a time
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": recipient,
                    "from": self.sender_id,
                    "sms": message,
                    "type": "plain",
                    "channel": "generic"
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
                        cost=ProviderCosts.TERMII_SMS,
                        sent_at=datetime.utcnow()
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Termii SMS error sending to {recipient}: {error_message}")
                    
                    return NotificationResponse(
                        success=False,
                        recipient=recipient,
                        provider=self.provider_name,
                        status=NotificationStatus.FAILED,
                        error=error_message,
                        cost=0.0
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending SMS to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending SMS via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
