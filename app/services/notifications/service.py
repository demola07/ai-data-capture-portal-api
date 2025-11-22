"""
Main Notification Service with batch processing and logging.
"""
import uuid
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.notifications.factory import get_email_provider, get_sms_provider, get_whatsapp_provider
from app.services.notifications.base import NotificationResponse, BatchNotificationResult
from app.services.notifications.template_renderer import TemplateRenderer
from app.models import NotificationBatch, NotificationLog, NotificationTemplate
from app.constants import NotificationType, NotificationStatus

logger = logging.getLogger(__name__)

# Concurrency settings
MAX_CONCURRENT_SENDS = 50  # Send up to 50 emails concurrently
BATCH_SIZE = 100  # Process in chunks of 100



class NotificationService:
    """Main notification service for sending emails, SMS, and WhatsApp messages"""
    
    def __init__(self, db: Session):
        self.db = db
        self._email_provider = None
        self._sms_provider = None
        self._whatsapp_provider = None
    
    @property
    def email_provider(self):
        """Lazy load email provider only when needed"""
        if self._email_provider is None:
            self._email_provider = get_email_provider()
        return self._email_provider
    
    @property
    def sms_provider(self):
        """Lazy load SMS provider only when needed"""
        if self._sms_provider is None:
            self._sms_provider = get_sms_provider()
        return self._sms_provider
    
    @property
    def whatsapp_provider(self):
        """Lazy load WhatsApp provider only when needed"""
        if self._whatsapp_provider is None:
            self._whatsapp_provider = get_whatsapp_provider()
        return self._whatsapp_provider
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """Send email to one or more recipients with concurrent processing"""
        batch_id = str(uuid.uuid4())
        
        # Create batch record
        batch = NotificationBatch(
            batch_id=batch_id,
            type=NotificationType.EMAIL,
            subject=subject,
            total_recipients=len(to),
            provider=self.email_provider.provider_name,
            created_by=user_id
        )
        self.db.add(batch)
        self.db.commit()
        
        # Send concurrently in batches
        all_results = []
        
        # Process in chunks to avoid overwhelming the system
        for i in range(0, len(to), BATCH_SIZE):
            chunk = to[i:i + BATCH_SIZE]
            
            # Create tasks for concurrent sending
            tasks = [
                self._send_single_email(recipient, subject, body, html_body, batch_id)
                for recipient in chunk
            ]
            
            # Send concurrently with limit
            chunk_results = await self._send_concurrent(tasks, MAX_CONCURRENT_SENDS)
            all_results.extend(chunk_results)
            
            logger.info(f"Processed {len(all_results)}/{len(to)} emails")
        
        # Update batch summary
        await self._update_batch_summary(batch_id, all_results)
        
        return self._create_batch_result(batch_id, all_results)
    
    async def _send_single_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        html_body: Optional[str],
        batch_id: str
    ) -> NotificationResponse:
        """Send email to a single recipient"""
        try:
            result = await self.email_provider.send_email(
                to=[recipient],
                subject=subject,
                body=body,
                html_body=html_body
            )
            
            # Log individual send
            await self._log_notification(batch_id, result, subject, body)
            return result
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {str(e)}")
            error_result = NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.email_provider.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e)
            )
            await self._log_notification(batch_id, error_result, subject, body)
            return error_result
    
    async def _send_concurrent(
        self,
        tasks: List,
        max_concurrent: int
    ) -> List[NotificationResponse]:
        """Send tasks concurrently with a limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        return await asyncio.gather(*[bounded_task(task) for task in tasks])

    
    async def send_sms(
        self,
        to: List[str],
        message: str,
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """Send SMS to one or more recipients with concurrent processing"""
        batch_id = str(uuid.uuid4())
        
        # Create batch record
        batch = NotificationBatch(
            batch_id=batch_id,
            type=NotificationType.SMS,
            total_recipients=len(to),
            provider=self.sms_provider.provider_name,
            created_by=user_id
        )
        self.db.add(batch)
        self.db.commit()
        
        # Send concurrently in batches
        all_results = []
        
        for i in range(0, len(to), BATCH_SIZE):
            chunk = to[i:i + BATCH_SIZE]
            
            tasks = [
                self._send_single_sms(recipient, message, batch_id)
                for recipient in chunk
            ]
            
            chunk_results = await self._send_concurrent(tasks, MAX_CONCURRENT_SENDS)
            all_results.extend(chunk_results)
            
            logger.info(f"Processed {len(all_results)}/{len(to)} SMS")
        
        await self._update_batch_summary(batch_id, all_results)
        return self._create_batch_result(batch_id, all_results)
    
    async def _send_single_sms(
        self,
        recipient: str,
        message: str,
        batch_id: str
    ) -> NotificationResponse:
        """Send SMS to a single recipient"""
        try:
            result = await self.sms_provider.send_sms(
                to=[recipient],
                message=message
            )
            await self._log_notification(batch_id, result, None, message)
            return result
            
        except Exception as e:
            logger.error(f"Error sending SMS to {recipient}: {str(e)}")
            error_result = NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.sms_provider.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e)
            )
            await self._log_notification(batch_id, error_result, None, message)
            return error_result

    
    async def send_whatsapp(
        self,
        to: List[str],
        message: str,
        template_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """Send WhatsApp message to one or more recipients with concurrent processing"""
        batch_id = str(uuid.uuid4())
        
        # Create batch record
        batch = NotificationBatch(
            batch_id=batch_id,
            type=NotificationType.WHATSAPP,
            total_recipients=len(to),
            provider=self.whatsapp_provider.provider_name,
            created_by=user_id
        )
        self.db.add(batch)
        self.db.commit()
        
        # Send concurrently in batches
        all_results = []
        
        for i in range(0, len(to), BATCH_SIZE):
            chunk = to[i:i + BATCH_SIZE]
            
            tasks = [
                self._send_single_whatsapp(recipient, message, template_id, batch_id)
                for recipient in chunk
            ]
            
            chunk_results = await self._send_concurrent(tasks, MAX_CONCURRENT_SENDS)
            all_results.extend(chunk_results)
            
            logger.info(f"Processed {len(all_results)}/{len(to)} WhatsApp messages")
        
        await self._update_batch_summary(batch_id, all_results)
        return self._create_batch_result(batch_id, all_results)
    
    async def _send_single_whatsapp(
        self,
        recipient: str,
        message: str,
        template_id: Optional[str],
        batch_id: str
    ) -> NotificationResponse:
        """Send WhatsApp message to a single recipient"""
        try:
            result = await self.whatsapp_provider.send_whatsapp(
                to=[recipient],
                message=message,
                template_id=template_id
            )
            await self._log_notification(batch_id, result, None, message)
            return result
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp to {recipient}: {str(e)}")
            error_result = NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.whatsapp_provider.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e)
            )
            await self._log_notification(batch_id, error_result, None, message)
            return error_result

    
    async def _log_notification(
        self,
        batch_id: str,
        result: NotificationResponse,
        subject: Optional[str],
        message: str
    ):
        """Log individual notification to database"""
        log = NotificationLog(
            batch_id=batch_id,
            recipient_type="email" if "@" in result.recipient else "phone",
            recipient=result.recipient,
            subject=subject,
            message=message,
            status=result.status,
            provider=result.provider,
            provider_message_id=result.message_id,
            error_message=result.error,
            cost=str(result.cost),
            sent_at=result.sent_at
        )
        self.db.add(log)
        self.db.commit()
    
    async def _update_batch_summary(self, batch_id: str, results: List[NotificationResponse]):
        """Update batch summary with results"""
        batch = self.db.query(NotificationBatch).filter(
            NotificationBatch.batch_id == batch_id
        ).first()
        
        if batch:
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            total_cost = sum(r.cost for r in results)
            
            batch.successful = successful
            batch.failed = failed
            batch.total_cost = str(total_cost)
            batch.completed_at = datetime.utcnow()
            
            self.db.commit()
    
    def _create_batch_result(
        self,
        batch_id: str,
        results: List[NotificationResponse]
    ) -> BatchNotificationResult:
        """Create batch result summary"""
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        return BatchNotificationResult(
            total=len(results),
            successful=successful,
            failed=failed,
            results=results,
            batch_id=batch_id,
            summary={
                "sent": successful,
                "failed": failed,
                "total": len(results)
            }
        )
    
    async def send_with_template(
        self,
        template_name: str,
        recipients: List[Dict[str, str]],
        common_variables: Optional[Dict[str, str]] = None,
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """
        Send notifications using a template.
        
        Args:
            template_name: Name of the template to use
            recipients: List of recipient dicts with email/phone and custom variables
                       Example: [{"email": "user@example.com", "name": "John", "date": "Dec 26"}]
            common_variables: Variables that are same for all recipients
            user_id: ID of user sending the notification
            
        Returns:
            BatchNotificationResult with send results
        """
        # Get template
        template = self.db.query(NotificationTemplate).filter(
            NotificationTemplate.name == template_name,
            NotificationTemplate.is_active == True
        ).first()
        
        if not template:
            raise ValueError(f"Template '{template_name}' not found or inactive")
        
        # Prepare common variables
        common_vars = common_variables or {}
        common_vars.update({
            "current_date": datetime.now().strftime("%B %d, %Y"),
            "current_year": str(datetime.now().year),
            "organization_name": "YMR Counselling Unit",
            "support_email": "ymrcounsellingfollowup@gmail.com",
            "support_phone": "+234 816 249 5328",
            "community_group_link": "https://t.me/ymr_new_army_2025",
            "header_image": template.header_image or ""
        })


        
        results = []
        
        # Process each recipient
        for recipient_data in recipients:
            # Merge recipient-specific and common variables
            variables = {**common_vars, **recipient_data}
            
            # Render template
            rendered_subject = TemplateRenderer.render(template.subject or "", variables)
            rendered_body = TemplateRenderer.render(template.body, variables)
            rendered_html = TemplateRenderer.render(template.html_body or "", variables) if template.html_body else None
            
            # Determine recipient (email or phone)
            recipient_address = recipient_data.get("email") or recipient_data.get("phone")
            if not recipient_address:
                logger.error(f"No email or phone found in recipient data: {recipient_data}")
                continue
            
            # Send based on template type
            try:
                if template.type == NotificationType.EMAIL:
                    result = await self.send_email(
                        to=[recipient_address],
                        subject=rendered_subject,
                        body=rendered_body,
                        html_body=rendered_html,
                        user_id=user_id
                    )
                elif template.type == NotificationType.SMS:
                    result = await self.send_sms(
                        to=[recipient_address],
                        message=rendered_body,
                        user_id=user_id
                    )
                elif template.type == NotificationType.WHATSAPP:
                    result = await self.send_whatsapp(
                        to=[recipient_address],
                        message=rendered_body,
                        user_id=user_id
                    )
                else:
                    raise ValueError(f"Unknown template type: {template.type}")
                
                results.extend(result.results)
                
            except Exception as e:
                logger.error(f"Error sending to {recipient_address}: {str(e)}")
                error_result = NotificationResponse(
                    success=False,
                    recipient=recipient_address,
                    provider="template",
                    status=NotificationStatus.FAILED,
                    error=str(e)
                )
                results.append(error_result)
        
        # Create combined batch result
        batch_id = str(uuid.uuid4())
        return self._create_batch_result(batch_id, results)
