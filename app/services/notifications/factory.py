"""
Factory functions for creating notification providers.
"""
from app.config import settings
from app.services.notifications.base import EmailProvider, SMSProvider, WhatsAppProvider
from app.services.notifications.email.aws_ses import AWSEmailProvider
from app.services.notifications.sms.termii import TermiiSMSProvider
from app.services.notifications.sms.twilio import TwilioSMSProvider
from app.services.notifications.whatsapp.termii import TermiiWhatsAppProvider
from app.services.notifications.whatsapp.twilio import TwilioWhatsAppProvider
from app.constants import ErrorMessages


def get_email_provider() -> EmailProvider:
    """Get the configured email provider"""
    provider = settings.EMAIL_PROVIDER.lower()
    
    if provider == "aws_ses":
        if not settings.AWS_ACCESS_KEY or not settings.AWS_SECRET_KEY:
            raise ValueError(f"{ErrorMessages.MISSING_CREDENTIALS}: AWS SES - Please set AWS_ACCESS_KEY and AWS_SECRET_KEY")
        
        return AWSEmailProvider(
            aws_access_key=settings.AWS_ACCESS_KEY,
            aws_secret_key=settings.AWS_SECRET_KEY,
            region=settings.AWS_REGION,
            default_from_email=settings.DEFAULT_FROM_EMAIL
        )
    
    else:
        raise ValueError(f"{ErrorMessages.PROVIDER_NOT_FOUND}: {provider} - Only 'aws_ses' is supported for email")


def get_sms_provider() -> SMSProvider:
    """Get the configured SMS provider"""
    provider = settings.SMS_PROVIDER.lower()
    
    if provider == "termii":
        if not settings.TERMII_API_KEY:
            raise ValueError(f"{ErrorMessages.MISSING_CREDENTIALS}: Termii - Please set TERMII_API_KEY in your .env file")
        
        return TermiiSMSProvider(
            api_key=settings.TERMII_API_KEY,
            sender_id=settings.TERMII_SENDER_ID
        )
    
    elif provider == "twilio":
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise ValueError(f"{ErrorMessages.MISSING_CREDENTIALS}: Twilio - Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in your .env file")
        
        return TwilioSMSProvider(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            phone_number=settings.TWILIO_PHONE_NUMBER
        )
    
    else:
        raise ValueError(f"{ErrorMessages.PROVIDER_NOT_FOUND}: {provider} - Supported providers: 'termii', 'twilio'")


def get_whatsapp_provider() -> WhatsAppProvider:
    """Get the configured WhatsApp provider"""
    provider = settings.WHATSAPP_PROVIDER.lower()
    
    if provider == "termii":
        if not settings.TERMII_API_KEY:
            raise ValueError(f"{ErrorMessages.MISSING_CREDENTIALS}: Termii - Please set TERMII_API_KEY in your .env file")
        
        return TermiiWhatsAppProvider(
            api_key=settings.TERMII_API_KEY,
            sender_id=settings.TERMII_SENDER_ID
        )
    
    elif provider == "twilio":
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise ValueError(f"{ErrorMessages.MISSING_CREDENTIALS}: Twilio - Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in your .env file")
        
        return TwilioWhatsAppProvider(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            phone_number=settings.TWILIO_PHONE_NUMBER
        )
    
    else:
        raise ValueError(f"{ErrorMessages.PROVIDER_NOT_FOUND}: {provider} - Supported providers: 'termii', 'twilio'")

