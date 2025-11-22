"""
AWS SES Email Provider implementation.
"""
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional
from datetime import datetime
import logging

from app.services.notifications.base import EmailProvider, NotificationResponse
from app.constants import NotificationStatus, ProviderCosts

logger = logging.getLogger(__name__)


class AWSEmailProvider(EmailProvider):
    """AWS SES email provider implementation"""
    
    def __init__(self, aws_access_key: str, aws_secret_key: str, region: str, default_from_email: str):
        self.client = boto3.client(
            'ses',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        self.default_from_email = default_from_email
        self.provider_name = "aws_ses"
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> NotificationResponse:
        """Send email via AWS SES"""
        
        sender = from_email or self.default_from_email
        recipient = to[0] if len(to) == 1 else to[0]  # AWS SES sends to one recipient at a time
        
        try:
            # Prepare email body
            body_data = {'Text': {'Data': body, 'Charset': 'UTF-8'}}
            if html_body:
                body_data['Html'] = {'Data': html_body, 'Charset': 'UTF-8'}
            
            # Send email
            response = self.client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body_data
                }
            )
            
            return NotificationResponse(
                success=True,
                recipient=recipient,
                message_id=response['MessageId'],
                provider=self.provider_name,
                status=NotificationStatus.SENT,
                cost=ProviderCosts.AWS_SES_EMAIL,
                sent_at=datetime.utcnow()
            )
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            logger.error(f"AWS SES error sending to {recipient}: {error_message}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=error_message,
                cost=0.0
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email via AWS SES: {str(e)}")
            
            return NotificationResponse(
                success=False,
                recipient=recipient,
                provider=self.provider_name,
                status=NotificationStatus.FAILED,
                error=str(e),
                cost=0.0
            )
