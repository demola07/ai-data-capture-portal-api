"""
Constants for the notification service.
"""

# Notification Types
class NotificationType:
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


# Notification Status
class NotificationStatus:
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    REJECTED = "rejected"


# Provider Names
class EmailProvider:
    AWS_SES = "aws_ses"
    TERMII = "termii"


class SMSProvider:
    TERMII = "termii"
    TWILIO = "twilio"


class WhatsAppProvider:
    TERMII = "termii"
    TWILIO = "twilio"


# Cost per message (in USD)
class ProviderCosts:
    # Email
    AWS_SES_EMAIL = 0.0001  # $0.10 per 1000 emails
    TERMII_EMAIL = 0.0  # Free tier
    
    # SMS (Nigeria)
    TERMII_SMS = 0.003  # ~₦2.50
    TWILIO_SMS = 0.0075  # ~$0.0075
    
    # WhatsApp
    TERMII_WHATSAPP = 0.005
    TWILIO_WHATSAPP = 0.0042


# Rate Limits
class RateLimits:
    EMAIL_PER_MINUTE = 10
    SMS_PER_MINUTE = 5
    WHATSAPP_PER_MINUTE = 5
    BULK_MAX_RECIPIENTS = 1000


# Error Messages
class ErrorMessages:
    PROVIDER_NOT_FOUND = "Provider not configured"
    INVALID_EMAIL = "Invalid email address"
    INVALID_PHONE = "Invalid phone number"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
    BATCH_TOO_LARGE = f"Batch size exceeds maximum of {RateLimits.BULK_MAX_RECIPIENTS}"
    MISSING_CREDENTIALS = "Provider credentials not configured"
    SEND_FAILED = "Failed to send notification"
