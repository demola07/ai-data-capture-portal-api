"""
Notification API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.oauth2 import get_current_user
from app.models import User, NotificationBatch, NotificationLog
from app.schemas import (
    EmailRequest, SMSRequest, WhatsAppRequest,
    BatchNotificationResult, SendWithTemplateRequest
)
from app.services.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/email", response_model=BatchNotificationResult)
async def send_email(
    request: EmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send email to one or more recipients"""
    service = NotificationService(db)
    result = await service.send_email(
        to=request.to,
        subject=request.subject,
        body=request.body,
        html_body=request.html_body,
        user_id=current_user.id
    )
    return result


@router.post("/sms", response_model=BatchNotificationResult)
async def send_sms(
    request: SMSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send SMS to one or more recipients"""
    service = NotificationService(db)
    result = await service.send_sms(
        to=request.to,
        message=request.message,
        user_id=current_user.id
    )
    return result


@router.post("/whatsapp", response_model=BatchNotificationResult)
async def send_whatsapp(
    request: WhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send WhatsApp message to one or more recipients"""
    service = NotificationService(db)
    result = await service.send_whatsapp(
        to=request.to,
        message=request.message,
        template_id=request.template_id,
        user_id=current_user.id
    )
    return result


@router.get("/reports/batch/{batch_id}")
async def get_batch_report(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed report for a specific batch"""
    batch = db.query(NotificationBatch).filter(
        NotificationBatch.batch_id == batch_id
    ).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    logs = db.query(NotificationLog).filter(
        NotificationLog.batch_id == batch_id
    ).all()
    
    return {
        "batch": {
            "batch_id": batch.batch_id,
            "type": batch.type,
            "subject": batch.subject,
            "total_recipients": batch.total_recipients,
            "successful": batch.successful,
            "failed": batch.failed,
            "total_cost": float(batch.total_cost),
            "provider": batch.provider,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at
        },
        "summary": {
            "total": batch.total_recipients,
            "successful": batch.successful,
            "failed": batch.failed,
            "total_cost": float(batch.total_cost)
        },
        "details": [
            {
                "recipient": log.recipient,
                "status": log.status,
                "cost": float(log.cost),
                "error": log.error_message,
                "sent_at": log.sent_at
            }
            for log in logs
        ]
    }


@router.get("/reports/summary")
async def get_notification_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    notification_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary of all notifications within date range"""
    query = db.query(NotificationBatch)
    
    if start_date:
        query = query.filter(NotificationBatch.created_at >= start_date)
    if end_date:
        query = query.filter(NotificationBatch.created_at <= end_date)
    if notification_type:
        query = query.filter(NotificationBatch.type == notification_type)
    
    batches = query.all()
    
    total_sent = sum(b.successful for b in batches)
    total_failed = sum(b.failed for b in batches)
    total_cost = sum(float(b.total_cost) for b in batches)
    
    return {
        "total_batches": len(batches),
        "total_sent": total_sent,
        "total_failed": total_failed,
        "total_cost": total_cost,
        "by_type": {
            "email": sum(1 for b in batches if b.type == "email"),
            "sms": sum(1 for b in batches if b.type == "sms"),
            "whatsapp": sum(1 for b in batches if b.type == "whatsapp")
        }
    }


@router.post("/send-with-template", response_model=BatchNotificationResult)
async def send_with_template(
    request: SendWithTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send notifications using a template with variable substitution"""
    service = NotificationService(db)
    result = await service.send_with_template(
        template_name=request.template_name,
        recipients=request.recipients,
        common_variables=request.common_variables,
        user_id=current_user.id
    )
    return result

