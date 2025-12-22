"""
Notification API endpoints - Optimized for bulk operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
from sqlalchemy import desc

from app.database import get_db
from app.oauth2 import get_current_user
from app.models import User, NotificationLog
from app.schemas import (
    SMSRequest, WhatsAppRequest,
    BatchNotificationResult, NotificationLogsResponseWrapper
)
from app.services.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Email endpoint removed - focus on SMS/WhatsApp for now


@router.post("/sms", response_model=BatchNotificationResult)
async def send_sms(
    request: SMSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send SMS to one or more recipients via Termii.
    
    - **to**: List of phone numbers in international format (e.g., 2349012345678)
    - **message**: Text message to send
    - **channel**: Route type - 'generic' (promotional), 'dnd' (transactional), or 'voice'
    - **message_type**: 'plain' or 'unicode'
    
    Automatically uses bulk endpoint for multiple recipients (up to 100 per batch).
    """
    service = NotificationService(db)
    result = await service.send_sms(
        to=request.to,
        message=request.message,
        channel=request.channel,
        message_type=request.message_type,
        user_id=current_user.id
    )
    return result


@router.post("/whatsapp", response_model=BatchNotificationResult)
async def send_whatsapp(
    request: WhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send WhatsApp message to one or more recipients via Termii.
    
    - **to**: List of phone numbers in international format (e.g., 2349012345678)
    - **message**: Text message (optional if media is provided)
    - **media**: Optional media object with 'url' and 'caption' for images, audio, documents, or video
    
    Supported media formats:
    - Images: JPG, JPEG, PNG
    - Audio: MP3, OGG, AMR
    - Documents: PDF
    - Video: MP4 (must have audio track)
    
    Automatically uses bulk endpoint for multiple recipients (up to 100 per batch).
    """
    service = NotificationService(db)
    result = await service.send_whatsapp(
        to=request.to,
        message=request.message,
        media=request.media,
        user_id=current_user.id
    )
    return result


@router.get("/logs/{batch_id}")
async def get_batch_log(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed log for a specific notification batch.
    
    Returns a single log entry with summary statistics for the entire batch.
    """
    log = db.query(NotificationLog).filter(
        NotificationLog.batch_id == batch_id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification log not found"
        )
    
    # Parse recipient sample if exists
    import json
    recipient_sample = None
    if log.recipient_sample:
        try:
            recipient_sample = json.loads(log.recipient_sample)
        except:
            recipient_sample = []
    
    return {
        "status": "success",
        "data": {
            "id": log.id,
            "batch_id": log.batch_id,
            "type": log.type,
            "channel": log.channel,
            "message": log.message,
            "total_recipients": log.total_recipients,
            "recipient_sample": recipient_sample,
            "successful_count": log.successful_count,
            "failed_count": log.failed_count,
            "success_rate": round((log.successful_count / log.total_recipients * 100), 2) if log.total_recipients > 0 else 0,
            "provider": log.provider,
            "provider_message_id": log.provider_message_id,
            "total_cost": log.total_cost,
            "status": log.status,
            "error_message": log.error_message,
            "created_by_email": log.created_by_email,
            "created_at": log.created_at,
            "sent_at": log.sent_at,
            "completed_at": log.completed_at
        }
    }


@router.get("/logs", response_model=NotificationLogsResponseWrapper)
async def get_notification_logs(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    notification_type: Optional[str] = Query(None, description="Filter by type: sms, whatsapp"),
    channel: Optional[str] = Query(None, description="Filter by channel: generic, dnd, whatsapp, voice"),
    status: Optional[str] = Query(None, description="Filter by status: sent, failed, partial"),
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of notification logs with filters.
    
    Each log entry represents a batch send with summary statistics.
    """
    query = db.query(NotificationLog)
    
    # Apply filters
    if notification_type:
        query = query.filter(NotificationLog.type == notification_type)
    if channel:
        query = query.filter(NotificationLog.channel == channel)
    if status:
        query = query.filter(NotificationLog.status == status)
    if start_date:
        query = query.filter(NotificationLog.created_at >= start_date)
    if end_date:
        # Add one day to include the entire end_date
        from datetime import timedelta
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(NotificationLog.created_at <= end_datetime)
    
    # Get total count
    total_count = query.count()
    
    # Get paginated results, ordered by most recent first
    logs = query.order_by(desc(NotificationLog.created_at)).limit(limit).offset(skip).all()
    
    return NotificationLogsResponseWrapper(
        status="success",
        data=logs,
        total=total_count,
        message=f"Retrieved {len(logs)} notification log(s)"
    )


@router.get("/stats")
async def get_notification_stats(
    start_date: Optional[date] = Query(None, description="Stats from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Stats to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated statistics for notifications.
    
    Returns summary of total sends, costs, and success rates.
    """
    query = db.query(NotificationLog)
    
    if start_date:
        query = query.filter(NotificationLog.created_at >= start_date)
    if end_date:
        from datetime import timedelta
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(NotificationLog.created_at <= end_datetime)
    
    logs = query.all()
    
    # Calculate aggregates
    total_batches = len(logs)
    total_recipients = sum(log.total_recipients for log in logs)
    total_successful = sum(log.successful_count for log in logs)
    total_failed = sum(log.failed_count for log in logs)
    total_cost = sum(float(log.total_cost) for log in logs if log.total_cost)
    
    # Group by type
    by_type = {}
    for log in logs:
        if log.type not in by_type:
            by_type[log.type] = {
                "batches": 0,
                "recipients": 0,
                "successful": 0,
                "failed": 0,
                "cost": 0
            }
        by_type[log.type]["batches"] += 1
        by_type[log.type]["recipients"] += log.total_recipients
        by_type[log.type]["successful"] += log.successful_count
        by_type[log.type]["failed"] += log.failed_count
        by_type[log.type]["cost"] += float(log.total_cost) if log.total_cost else 0
    
    # Group by channel
    by_channel = {}
    for log in logs:
        if log.channel:
            if log.channel not in by_channel:
                by_channel[log.channel] = {
                    "batches": 0,
                    "recipients": 0,
                    "successful": 0,
                    "failed": 0
                }
            by_channel[log.channel]["batches"] += 1
            by_channel[log.channel]["recipients"] += log.total_recipients
            by_channel[log.channel]["successful"] += log.successful_count
            by_channel[log.channel]["failed"] += log.failed_count
    
    return {
        "status": "success",
        "data": {
            "summary": {
                "total_batches": total_batches,
                "total_recipients": total_recipients,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "success_rate": round((total_successful / total_recipients * 100), 2) if total_recipients > 0 else 0,
                "total_cost": round(total_cost, 2)
            },
            "by_type": by_type,
            "by_channel": by_channel
        }
    }

