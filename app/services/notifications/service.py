"""
Optimized Notification Service with bulk logging support.
"""
import uuid
import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.notifications.factory import get_email_provider, get_sms_provider, get_whatsapp_provider
from app.services.notifications.base import NotificationResponse
from app.models import NotificationLog, User
from app.schemas import BatchNotificationResult

logger = logging.getLogger(__name__)


class NotificationService:
    """Optimized notification service with single log entry per batch"""
    
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
        template_id: str,
        variables: Dict[str, str],
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """
        Send templated email using Termii - sends to recipients one by one with concurrent processing.
        
        Auto-fills:
        - convert_name: Fetched from Convert/Counsellee tables based on email
        - telegram_link: From config settings
        - current_year: Current year
        """
        import asyncio
        from app.config import settings
        from datetime import datetime
        from app.models import Convert, Counsellee
        
        batch_id = str(uuid.uuid4())
        
        # Auto-fill telegram_link from config if not provided
        if "telegram_link" not in variables and settings.TELEGRAM_LINK:
            variables["telegram_link"] = settings.TELEGRAM_LINK
        
        # Auto-fill current_year if not provided
        if "current_year" not in variables:
            variables["current_year"] = str(datetime.now().year)
        
        # Get user email for logging
        user_email = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            user_email = user.email if user else None
        
        # Fetch convert names from database if not provided in variables
        # Build a map of email -> name for personalization
        email_to_name = {}
        if "convert_name" not in variables:
            # Query all converts and counsellees with matching emails
            converts = self.db.query(Convert).filter(Convert.email.in_(to)).all()
            counsellees = self.db.query(Counsellee).filter(Counsellee.email.in_(to)).all()
            
            # Build email -> name mapping
            for convert in converts:
                if convert.email and convert.name:
                    email_to_name[convert.email] = convert.name
            
            for counsellee in counsellees:
                if counsellee.email and counsellee.name:
                    email_to_name[counsellee.email] = counsellee.name
        
        # Send emails concurrently with personalized names
        tasks = []
        for recipient in to:
            # Create personalized variables for each recipient
            recipient_vars = variables.copy()
            
            # If convert_name not in original variables, use fetched name or default
            if "convert_name" not in variables:
                recipient_vars["convert_name"] = email_to_name.get(recipient, "New Believer")
            
            tasks.append(self.email_provider.send_email(
                to=[recipient],
                subject=subject,
                template_id=template_id,
                variables=recipient_vars
            ))
        
        # Execute all sends concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        successful_count = sum(1 for r in results if isinstance(r, NotificationResponse) and r.success)
        failed_count = len(results) - successful_count
        
        # Get first successful result for metadata
        first_result = next((r for r in results if isinstance(r, NotificationResponse)), None)
        
        try:
            # Create single log entry for the batch
            log_entry = NotificationLog(
                batch_id=batch_id,
                type="email",
                channel="email",
                subject=subject,
                message=f"Template: {template_id}",
                total_recipients=len(to),
                recipient_sample=json.dumps(to[:3]),
                status="sent" if successful_count > 0 else "failed",
                successful_count=successful_count,
                failed_count=failed_count,
                provider=self.email_provider.provider_name,
                provider_message_id=first_result.message_id if first_result else None,
                provider_response=first_result.provider_response if first_result else None,
                total_cost="0",
                error_message=None if successful_count > 0 else "All emails failed",
                meta=json.dumps({"template_id": template_id, "variables": variables}),
                created_by=user_id,
                created_by_email=user_email,
                sent_at=datetime.utcnow() if successful_count > 0 else None,
                completed_at=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return BatchNotificationResult(
                status="success" if successful_count > 0 else "failed",
                batch_id=batch_id,
                total_recipients=len(to),
                successful_count=successful_count,
                failed_count=failed_count,
                total_cost="0",
                provider=self.email_provider.provider_name,
                message_id=first_result.message_id if first_result else None,
                message=f"Email sent successfully to {successful_count}/{len(to)} recipient(s)" if successful_count > 0 else "Failed to send emails"
            )
            
        except Exception as e:
            logger.error(f"Error logging email batch: {str(e)}")
            self.db.rollback()
            
            return BatchNotificationResult(
                status="failed",
                batch_id=batch_id,
                total_recipients=len(to),
                successful_count=0,
                failed_count=len(to),
                total_cost="0",
                provider=self.email_provider.provider_name,
                message_id=None,
                message=f"Failed to send emails: {str(e)}"
            )
    
    async def send_sms(
        self,
        to: List[str],
        message: str,
        channel: str = "generic",
        message_type: str = "plain",
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """Send SMS using Termii - automatically uses bulk endpoint for multiple recipients"""
        batch_id = str(uuid.uuid4())
        
        # Get user email for logging
        user_email = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            user_email = user.email if user else None
        
        try:
            # Send via provider (automatically handles bulk)
            result = await self.sms_provider.send_sms(
                to=to,
                message=message,
                channel=channel,
                message_type=message_type
            )
            
            # Create single log entry for the batch
            log_entry = NotificationLog(
                batch_id=batch_id,
                type="sms",
                channel=channel,
                subject=None,
                message=message,
                total_recipients=result.total_recipients or len(to),
                recipient_sample=json.dumps(to[:3]),  # Store first 3 as sample
                status=result.status,
                successful_count=result.successful_count or (len(to) if result.success else 0),
                failed_count=result.failed_count or (0 if result.success else len(to)),
                provider=result.provider,
                provider_message_id=result.message_id,
                provider_response=result.provider_response,
                total_cost=result.cost,
                error_message=result.error,
                meta=result.metadata,
                created_by=user_id,
                created_by_email=user_email,
                sent_at=result.sent_at or datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return BatchNotificationResult(
                status="success" if result.success else "failed",
                batch_id=batch_id,
                total_recipients=result.total_recipients or len(to),
                successful_count=result.successful_count or (len(to) if result.success else 0),
                failed_count=result.failed_count or (0 if result.success else len(to)),
                total_cost=result.cost,
                provider=result.provider,
                message_id=result.message_id,
                message=f"SMS sent successfully to {len(to)} recipient(s)" if result.success else f"Failed to send SMS: {result.error}"
            )
            
        except Exception as e:
            logger.error(f"Error sending SMS batch: {str(e)}")
            
            # Log the failure
            log_entry = NotificationLog(
                batch_id=batch_id,
                type="sms",
                channel=channel,
                subject=None,
                message=message,
                total_recipients=len(to),
                recipient_sample=json.dumps(to[:3]),
                status="failed",
                successful_count=0,
                failed_count=len(to),
                provider=self.sms_provider.provider_name,
                provider_message_id=None,
                provider_response=None,
                total_cost="0",
                error_message=str(e),
                meta=None,
                created_by=user_id,
                created_by_email=user_email,
                sent_at=None,
                completed_at=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return BatchNotificationResult(
                status="failed",
                batch_id=batch_id,
                total_recipients=len(to),
                successful_count=0,
                failed_count=len(to),
                total_cost="0",
                provider=self.sms_provider.provider_name,
                message_id=None,
                message=f"Failed to send SMS: {str(e)}"
            )
    
    async def send_whatsapp(
        self,
        to: List[str],
        message: Optional[str] = None,
        media: Optional[Dict[str, str]] = None,
        user_id: Optional[int] = None
    ) -> BatchNotificationResult:
        """Send WhatsApp message - automatically uses bulk endpoint for multiple recipients"""
        batch_id = str(uuid.uuid4())
        
        # Get user email for logging
        user_email = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            user_email = user.email if user else None
        
        # Validate input
        if not message and not media:
            return BatchNotificationResult(
                status="failed",
                batch_id=batch_id,
                total_recipients=len(to),
                successful_count=0,
                failed_count=len(to),
                total_cost="0",
                provider=self.whatsapp_provider.provider_name,
                message_id=None,
                message="Either message or media must be provided"
            )
        
        try:
            # Send via provider (automatically handles bulk)
            result = await self.whatsapp_provider.send_whatsapp(
                to=to,
                message=message or "",
                media=media
            )
            
            # Create single log entry for the batch
            log_entry = NotificationLog(
                batch_id=batch_id,
                type="whatsapp",
                channel="whatsapp",
                subject=None,
                message=message or f"Media: {media.get('caption', 'No caption')}" if media else "",
                total_recipients=result.total_recipients or len(to),
                recipient_sample=json.dumps(to[:3]),
                status=result.status,
                successful_count=result.successful_count or (len(to) if result.success else 0),
                failed_count=result.failed_count or (0 if result.success else len(to)),
                provider=result.provider,
                provider_message_id=result.message_id,
                provider_response=result.provider_response,
                total_cost=result.cost,
                error_message=result.error,
                meta=result.metadata,
                created_by=user_id,
                created_by_email=user_email,
                sent_at=result.sent_at or datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return BatchNotificationResult(
                status="success" if result.success else "failed",
                batch_id=batch_id,
                total_recipients=result.total_recipients or len(to),
                successful_count=result.successful_count or (len(to) if result.success else 0),
                failed_count=result.failed_count or (0 if result.success else len(to)),
                total_cost=result.cost,
                provider=result.provider,
                message_id=result.message_id,
                message=f"WhatsApp sent successfully to {len(to)} recipient(s)" if result.success else f"Failed to send WhatsApp: {result.error}"
            )
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp batch: {str(e)}")
            
            # Log the failure
            log_entry = NotificationLog(
                batch_id=batch_id,
                type="whatsapp",
                channel="whatsapp",
                subject=None,
                message=message or f"Media: {media.get('caption', 'No caption')}" if media else "",
                total_recipients=len(to),
                recipient_sample=json.dumps(to[:3]),
                status="failed",
                successful_count=0,
                failed_count=len(to),
                provider=self.whatsapp_provider.provider_name,
                provider_message_id=None,
                provider_response=None,
                total_cost="0",
                error_message=str(e),
                meta=json.dumps({"media": media}) if media else None,
                created_by=user_id,
                created_by_email=user_email,
                sent_at=None,
                completed_at=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return BatchNotificationResult(
                status="failed",
                batch_id=batch_id,
                total_recipients=len(to),
                successful_count=0,
                failed_count=len(to),
                total_cost="0",
                provider=self.whatsapp_provider.provider_name,
                message_id=None,
                message=f"Failed to send WhatsApp: {str(e)}"
            )
