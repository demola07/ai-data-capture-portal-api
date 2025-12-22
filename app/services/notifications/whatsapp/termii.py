"""
Termii WhatsApp Provider implementation with media support.
"""
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from app.services.notifications.base import WhatsAppProvider, NotificationResponse
from app.constants import NotificationStatus

logger = logging.getLogger(__name__)


class TermiiWhatsAppProvider(WhatsAppProvider):
    """Termii WhatsApp provider implementation with bulk and media support"""
    
    BASE_URL = "https://v3.api.termii.com"
    WHATSAPP_ENDPOINT = f"{BASE_URL}/api/sms/send"
    
    def __init__(self, api_key: str, sender_id: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.provider_name = "termii"
    
    async def send_whatsapp(
        self,
        to: List[str],
        message: str,
        media: Optional[Dict[str, str]] = None
    ) -> NotificationResponse:
        """
        Send WhatsApp message via Termii API
        
        Args:
            to: List of phone numbers (international format)
            message: Message text (not used if media is provided)
            media: Optional dict with 'url' and 'caption' for media messages
        """
        
        # Use bulk endpoint if sending to multiple recipients
        if len(to) > 1:
            return await self.send_bulk_whatsapp(to, message, media)
        
        recipient = to[0]
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": recipient,
                    "from": self.sender_id,
                    "type": "plain",
                    "channel": "whatsapp"
                }
                
                # Add media or text message
                if media:
                    payload["media"] = media
                else:
                    payload["sms"] = message
                
                response = await client.post(
                    self.WHATSAPP_ENDPOINT,
                    json=payload,
                    timeout=30.0
                )
                
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("code") == "ok":
                    metadata = {"media": media} if media else None
                    
                    return NotificationResponse(
                        success=True,
                        recipient=recipient,
                        message_id=response_data.get("message_id"),
                        provider=self.provider_name,
                        status=NotificationStatus.SENT,
                        cost=str(response_data.get("balance", 0)),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data),
                        metadata=json.dumps(metadata) if metadata else None
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
                        cost="0",
                        provider_response=json.dumps(response_data)
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending WhatsApp to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost="0"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost="0"
            )
    
    async def send_bulk_whatsapp(
        self,
        to: List[str],
        message: str,
        media: Optional[Dict[str, str]] = None
    ) -> NotificationResponse:
        """Send bulk WhatsApp messages via Termii API (up to 100 recipients)"""
        
        # Termii accepts max 100 numbers per request
        batch_size = 100
        all_recipients = to[:batch_size]
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": all_recipients,
                    "from": self.sender_id,
                    "type": "plain",
                    "channel": "whatsapp"
                }
                
                # Add media or text message
                if media:
                    payload["media"] = media
                else:
                    payload["sms"] = message
                
                response = await client.post(
                    self.WHATSAPP_ENDPOINT,
                    json=payload,
                    timeout=60.0
                )
                
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("code") == "ok":
                    metadata = {"media": media} if media else None
                    
                    return NotificationResponse(
                        success=True,
                        recipient="bulk",
                        message_id=response_data.get("message_id"),
                        provider=self.provider_name,
                        status=NotificationStatus.SENT,
                        cost=str(response_data.get("balance", 0)),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data),
                        metadata=json.dumps(metadata) if metadata else None,
                        total_recipients=len(all_recipients),
                        successful_count=len(all_recipients),
                        failed_count=0
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Termii bulk WhatsApp error: {error_message}")
                    
                    return NotificationResponse(
                        success=False,
                        recipient="bulk",
                        provider=self.provider_name,
                        status=NotificationStatus.FAILED,
                        error=error_message,
                        cost="0",
                        provider_response=json.dumps(response_data),
                        total_recipients=len(all_recipients),
                        successful_count=0,
                        failed_count=len(all_recipients)
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending bulk WhatsApp via Termii")
            return NotificationResponse(
                success=False,
                recipient="bulk",
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost="0",
                total_recipients=len(all_recipients),
                successful_count=0,
                failed_count=len(all_recipients)
            )
        except Exception as e:
            logger.error(f"Unexpected error sending bulk WhatsApp via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient="bulk",
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost="0",
                total_recipients=len(all_recipients),
                successful_count=0,
                failed_count=len(all_recipients)
            )
