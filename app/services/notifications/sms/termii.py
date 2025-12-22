"""Termii SMS Provider implementation."""
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from app.services.notifications.base import SMSProvider, NotificationResponse
from app.constants import NotificationStatus

logger = logging.getLogger(__name__)


class TermiiSMSProvider(SMSProvider):
    """Termii SMS provider implementation with bulk support"""
    
    BASE_URL = "https://v3.api.termii.com"
    SINGLE_SMS_ENDPOINT = f"{BASE_URL}/api/sms/send"
    BULK_SMS_ENDPOINT = f"{BASE_URL}/api/sms/send/bulk"
    
    def __init__(self, api_key: str, sender_id: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.provider_name = "termii"
    
    async def send_sms(
        self,
        to: List[str],
        message: str,
        channel: str = "generic",
        message_type: str = "plain"
    ) -> NotificationResponse:
        """Send SMS via Termii API - automatically uses bulk endpoint for multiple recipients"""
        
        # Use bulk endpoint if sending to multiple recipients
        if len(to) > 1:
            return await self.send_bulk_sms(to, message, channel, message_type)
        
        # Single SMS
        recipient = to[0]
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": recipient,
                    "from": self.sender_id,
                    "sms": message,
                    "type": message_type,
                    "channel": channel
                }
                
                response = await client.post(
                    self.SINGLE_SMS_ENDPOINT,
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
                        cost=str(response_data.get("balance", 0)),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data)
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
                        cost="0",
                        provider_response=json.dumps(response_data)
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending SMS to {recipient} via Termii")
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost="0"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending SMS via Termii: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost="0"
            )
    
    async def send_bulk_sms(
        self,
        to: List[str],
        message: str,
        channel: str = "generic",
        message_type: str = "plain"
    ) -> NotificationResponse:
        """Send bulk SMS via Termii API (up to 100 recipients per batch)"""
        
        # Termii accepts max 100 numbers per request
        batch_size = 100
        all_recipients = to[:batch_size]  # Take first 100 if more provided
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": all_recipients,
                    "from": self.sender_id,
                    "sms": message,
                    "type": message_type,
                    "channel": channel
                }
                
                response = await client.post(
                    self.BULK_SMS_ENDPOINT,
                    json=payload,
                    timeout=60.0  # Longer timeout for bulk
                )
                
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("code") == "ok":
                    return NotificationResponse(
                        success=True,
                        recipient="bulk",
                        message_id=response_data.get("message_id"),
                        provider=self.provider_name,
                        status=NotificationStatus.SENT,
                        cost=str(response_data.get("balance", 0)),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data),
                        total_recipients=len(all_recipients),
                        successful_count=len(all_recipients),
                        failed_count=0
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Termii bulk SMS error: {error_message}")
                    
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
            logger.error(f"Timeout sending bulk SMS via Termii")
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
            logger.error(f"Unexpected error sending bulk SMS via Termii: {str(e)}")
            
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
