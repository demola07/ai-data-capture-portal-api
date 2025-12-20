"""
Twilio SMS Provider implementation.
"""
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import List
from datetime import datetime
import logging

from app.services.notifications.base import SMSProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS provider implementation"""
    
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        self.client = Client(account_sid, auth_token)
        self.phone_number = phone_number
        self.provider_name = "twilio"
    
    async def send_sms(
        self,
        to: List[str],
        message: str
    ) -> NotificationResponse:
        """Send SMS via Twilio API"""
        
        recipient = to[0] if len(to) == 1 else to[0]  # Send to one recipient at a time
        
        try:
            # Twilio client is synchronous, but we're in an async context
            # In production, consider using twilio-async or running in executor
            message_response = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=recipient
            )
            
            return NotificationResponse(
                success=True,
                recipient=recipient,
                message_id=message_response.sid,
                provider=self.provider_name,
                status=NotificationStatus.SENT,
                cost=ProviderCosts.TWILIO_SMS,
                sent_at=datetime.utcnow()
            )
            
        except TwilioRestException as e:
            logger.error(f"Twilio SMS error sending to {recipient}: {e.msg}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=e.msg,
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending SMS via Twilio: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
