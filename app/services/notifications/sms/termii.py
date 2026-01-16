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
        """
        Send bulk SMS via Termii API with automatic batching.
        
        Termii accepts max 100 numbers per request. This method automatically
        splits large recipient lists into batches of 100 and sends them all.
        """
        import asyncio
        
        batch_size = 100
        total_recipients = len(to)
        
        # Split recipients into batches of 100
        batches = [to[i:i + batch_size] for i in range(0, len(to), batch_size)]
        
        logger.info(f"Sending SMS to {total_recipients} recipients in {len(batches)} batch(es)")
        
        # Send all batches concurrently
        tasks = []
        for batch_num, batch in enumerate(batches, 1):
            tasks.append(self._send_single_batch(batch, message, channel, message_type, batch_num))
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        total_successful = 0
        total_failed = 0
        total_cost = 0.0
        all_message_ids = []
        errors = []
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch failed with exception: {str(result)}")
                errors.append(str(result))
                total_failed += batch_size  # Assume all failed
            elif isinstance(result, NotificationResponse):
                if result.success:
                    total_successful += result.successful_count or 0
                    if result.message_id:
                        all_message_ids.append(result.message_id)
                    if result.cost:
                        try:
                            total_cost += float(result.cost)
                        except (ValueError, TypeError):
                            pass
                else:
                    total_failed += result.failed_count or 0
                    if result.error:
                        errors.append(result.error)
        
        # Determine overall success
        overall_success = total_successful > 0 and total_failed == 0
        
        return NotificationResponse(
            success=overall_success,
            recipient="bulk",
            message_id=",".join(all_message_ids) if all_message_ids else None,
            provider=self.provider_name,
            status=NotificationStatus.SENT if overall_success else NotificationStatus.FAILED,
            cost=str(total_cost),
            sent_at=datetime.utcnow() if overall_success else None,
            provider_response=json.dumps({
                "batches": len(batches),
                "total_recipients": total_recipients,
                "successful": total_successful,
                "failed": total_failed,
                "errors": errors if errors else None
            }),
            total_recipients=total_recipients,
            successful_count=total_successful,
            failed_count=total_failed,
            error="; ".join(errors) if errors else None
        )
    
    async def _send_single_batch(
        self,
        recipients: List[str],
        message: str,
        channel: str,
        message_type: str,
        batch_num: int
    ) -> NotificationResponse:
        """Send a single batch of up to 100 recipients"""
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "to": recipients,
                    "from": self.sender_id,
                    "sms": message,
                    "type": message_type,
                    "channel": channel
                }
                
                logger.info(f"Sending batch {batch_num} with {len(recipients)} recipients")
                
                response = await client.post(
                    self.BULK_SMS_ENDPOINT,
                    json=payload,
                    timeout=60.0
                )
                
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("code") == "ok":
                    logger.info(f"Batch {batch_num} sent successfully")
                    return NotificationResponse(
                        success=True,
                        recipient=f"batch_{batch_num}",
                        message_id=response_data.get("message_id"),
                        provider=self.provider_name,
                        status=NotificationStatus.SENT,
                        cost=str(response_data.get("balance", 0)),
                        sent_at=datetime.utcnow(),
                        provider_response=json.dumps(response_data),
                        total_recipients=len(recipients),
                        successful_count=len(recipients),
                        failed_count=0
                    )
                else:
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Batch {batch_num} failed: {error_message}")
                    
                    return NotificationResponse(
                        success=False,
                        recipient=f"batch_{batch_num}",
                        provider=self.provider_name,
                        status=NotificationStatus.FAILED,
                        error=error_message,
                        cost="0",
                        provider_response=json.dumps(response_data),
                        total_recipients=len(recipients),
                        successful_count=0,
                        failed_count=len(recipients)
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Batch {batch_num} timeout")
            return NotificationResponse(
                success=False,
                recipient=f"batch_{batch_num}",
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error="Request timeout",
                cost="0",
                total_recipients=len(recipients),
                successful_count=0,
                failed_count=len(recipients)
            )
        except Exception as e:
            logger.error(f"Batch {batch_num} error: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=f"batch_{batch_num}",
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost="0",
                total_recipients=len(recipients),
                successful_count=0,
                failed_count=len(recipients)
            )
