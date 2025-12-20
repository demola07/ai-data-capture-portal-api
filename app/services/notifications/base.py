"""
Base abstract classes for notification providers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    """Response from a single notification send"""
    success: bool
    recipient: str  # email or phone number
    message_id: Optional[str] = None
    provider: str
    status: str  # "sent", "failed", "pending"
    error: Optional[str] = None
    cost: float = 0.0
    sent_at: Optional[datetime] = None


class BatchNotificationResult(BaseModel):
    """Result from a batch notification send"""
    total: int
    successful: int
    failed: int
    results: List[NotificationResponse]
    batch_id: str
    summary: dict  # {"sent": 10, "failed": 2, "pending": 0}


class EmailProvider(ABC):
    """Abstract base class for email providers"""
    
    @abstractmethod
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> NotificationResponse:
        """Send an email to one or more recipients"""
        pass


class SMSProvider(ABC):
    """Abstract base class for SMS providers"""
    
    @abstractmethod
    async def send_sms(
        self,
        to: List[str],
        message: str
    ) -> NotificationResponse:
        """Send an SMS to one or more recipients"""
        pass


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers"""
    
    @abstractmethod
    async def send_whatsapp(
        self,
        to: List[str],
        message: str,
        template_id: Optional[str] = None
    ) -> NotificationResponse:
        """Send a WhatsApp message to one or more recipients"""
        pass
