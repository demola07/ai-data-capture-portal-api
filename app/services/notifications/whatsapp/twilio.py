"""
Twilio WhatsApp Provider implementation.
"""
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import List, Optional
from datetime import datetime
import logging

from app.services.notifications.base import WhatsAppProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider(WhatsAppProvider):
    """Twilio WhatsApp provider implementation"""
    
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        self.client = Client(account_sid, auth_token)
        self.phone_number = f"whatsapp:{phone_number}"  # Twilio WhatsApp format
        self.provider_name = "twilio"
    
    async def send_whatsapp(
        self,
        to: List[str],
        message: str,
        template_id: Optional[str] = None
    ) -> NotificationResponse:
        """Send WhatsApp message via Twilio API"""
        
        recipient = to[0] if len(to) == 1 else to[0]  # Send to one recipient at a time
        whatsapp_recipient = f"whatsapp:{recipient}"  # Format for Twilio
        
        try:
            # Twilio client is synchronous
            message_response = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=whatsapp_recipient
            )
            
            return NotificationResponse(
                success=True,
                recipient=recipient,
                message_id=message_response.sid,
                provider=self.provider_name,
                status=NotificationStatus.SENT,
                cost=ProviderCosts.TWILIO_WHATSAPP,
                sent_at=datetime.utcnow()
            )
            
        except TwilioRestException as e:
            logger.error(f"Twilio WhatsApp error sending to {recipient}: {e.msg}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=e.msg,
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp via Twilio: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
