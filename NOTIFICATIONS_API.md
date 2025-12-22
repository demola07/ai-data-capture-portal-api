# Notifications API Documentation

## Overview

The notification system has been restructured for efficiency with Termii as the primary provider for SMS and WhatsApp messaging. The system now uses optimized bulk logging - one log entry per batch instead of per recipient.

## Provider: Termii

**Base URL:** `https://v3.api.termii.com`

**Configuration:**
- API Key: Set in `.env` as `TERMII_API_KEY`
- Sender ID: Set in `.env` as `TERMII_SENDER_ID`

## Features

### SMS Messaging
- ✅ Single SMS
- ✅ Bulk SMS (up to 100 recipients per batch)
- ✅ DND (Transactional) channel support
- ✅ Generic (Promotional) channel support
- ✅ Voice channel support (text-to-speech)

### WhatsApp Messaging
- ✅ Single WhatsApp message
- ✅ Bulk WhatsApp (up to 100 recipients per batch)
- ✅ Media support (images, audio, documents, video)
- ✅ Text messages with captions

## Notification Logging Structure

### Optimized for Bulk Operations

Instead of logging each recipient individually, the system now creates **one log entry per batch** with summary statistics:

```json
{
  "id": 1,
  "batch_id": "uuid-here",
  "type": "sms",
  "channel": "dnd",
  "subject": null,
  "message": "Your verification code is 123456",
  "total_recipients": 150,
  "recipient_sample": "[\"2349012345678\", \"2349087654321\", \"2349011111111\"]",
  "status": "sent",
  "successful_count": 148,
  "failed_count": 2,
  "provider": "termii",
  "provider_message_id": "3017544054459083819856413",
  "provider_response": "{\"code\":\"ok\",\"balance\":1047.57,\"message\":\"Successfully Sent\"}",
  "total_cost": "1047.57",
  "error_message": null,
  "metadata": null,
  "created_by": 1,
  "created_by_email": "admin@example.com",
  "created_at": "2025-12-22T18:00:00Z",
  "sent_at": "2025-12-22T18:00:01Z",
  "completed_at": "2025-12-22T18:00:05Z"
}
```

### Benefits
- **Reduced database size**: 100 recipients = 1 log entry (vs 100 entries)
- **Faster queries**: Fewer rows to scan
- **Better analytics**: Summary stats readily available
- **Frontend-friendly**: Easy to display in tables

## API Endpoints (To Be Implemented)

### Send SMS

```http
POST /api/notifications/sms
Authorization: Bearer {token}
Content-Type: application/json

{
  "to": ["2349012345678", "2349087654321"],
  "message": "Your verification code is 123456",
  "channel": "dnd",  // or "generic", "voice"
  "type": "plain"    // or "unicode"
}
```

**Response:**
```json
{
  "status": "success",
  "batch_id": "uuid-here",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "message_id": "3017544054459083819856413",
  "cost": "1047.57"
}
```

### Send WhatsApp

```http
POST /api/notifications/whatsapp
Authorization: Bearer {token}
Content-Type: application/json

{
  "to": ["2349012345678", "2349087654321"],
  "message": "Hello from YMR!",
  "media": {
    "url": "https://example.com/image.jpg",
    "caption": "Check this out!"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "batch_id": "uuid-here",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "message_id": "3017544054459083819856413",
  "cost": "1047.57"
}
```

### Get Notification Logs

```http
GET /api/notifications/logs?limit=20&skip=0&type=sms
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "batch_id": "uuid-here",
      "type": "sms",
      "channel": "dnd",
      "message": "Your verification code is...",
      "total_recipients": 150,
      "successful_count": 148,
      "failed_count": 2,
      "provider": "termii",
      "total_cost": "1047.57",
      "created_by_email": "admin@example.com",
      "created_at": "2025-12-22T18:00:00Z",
      "status": "sent"
    }
  ],
  "total": 50
}
```

## Channel Types (Termii)

### 1. Generic (Promotional)
- For marketing and promotional messages
- **Does NOT deliver to DND numbers**
- **Time restrictions**: No delivery between 8PM-8AM WAT for MTN Nigeria
- Lower cost
- Use for: newsletters, promotions, announcements

### 2. DND (Transactional)
- Delivers to ALL numbers including DND
- No time restrictions
- Higher cost
- **Recommended for**: OTPs, password resets, critical alerts
- Requires activation on Termii account

### 3. WhatsApp
- Delivers via WhatsApp
- Supports media (images, audio, documents, video)
- Conversational messaging
- Good delivery rates

### 4. Voice
- Converts text to speech
- Delivers as automated voice call
- **Important**: Add spaces between OTP digits for better interpretation
- Example: "Your code is 1 2 3 4 5 6" instead of "123456"

## Media Support (WhatsApp Only)

### Supported Formats

| Type | Formats |
|------|---------|
| Image | JPG, JPEG, PNG |
| Audio | MP3, OGG, AMR |
| Documents | PDF |
| Video | MP4 (must have audio track) |

### Media Payload Example

```json
{
  "to": ["2349012345678"],
  "media": {
    "url": "https://media.example.com/document.pdf",
    "caption": "Your invoice for December"
  }
}
```

**Note**: When using `media`, don't include the `message` field.

## Cost Tracking

- All costs are stored as strings to avoid floating-point precision issues
- Termii returns the remaining balance after each send
- Frontend can display costs and track spending per batch

## Error Handling

### Common Errors

1. **Invalid phone number format**
   - Must be international format: `2349012345678`
   - No spaces, dashes, or plus signs

2. **Batch size exceeded**
   - Max 100 recipients per batch
   - Split larger lists into multiple batches

3. **Insufficient balance**
   - Check Termii account balance
   - Top up as needed

4. **DND channel not activated**
   - Contact Termii support to activate
   - Use generic channel for non-critical messages

## Best Practices

1. **Use DND channel for OTPs and critical messages**
2. **Batch recipients in groups of 100**
3. **Store recipient samples (first 3) for reference**
4. **Monitor success/failure rates**
5. **For voice OTPs, add spaces between digits**
6. **Use WhatsApp for rich media content**
7. **Check balance before large campaigns**

## Migration

The database migration `876ab23eb3c0` restructures the notification tables:
- Drops old `notification_batches` and `notification_logs` tables
- Creates new optimized `notification_logs` table
- Adds indexes for faster queries

**Run migration:**
```bash
alembic upgrade head
```

## Frontend Integration

### Display Notification Logs

```typescript
interface NotificationLog {
  id: number;
  batch_id: string;
  type: 'sms' | 'whatsapp' | 'email';
  channel?: 'dnd' | 'generic' | 'whatsapp' | 'voice';
  message: string;
  total_recipients: number;
  successful_count: number;
  failed_count: number;
  provider: string;
  total_cost: string;
  status: 'sent' | 'failed' | 'partial' | 'pending';
  created_by_email?: string;
  created_at: string;
}
```

### Success Rate Calculation

```typescript
const successRate = (log: NotificationLog) => {
  return (log.successful_count / log.total_recipients) * 100;
};
```

### Status Badge Colors

- `sent` → Green (100% success)
- `partial` → Yellow (some failures)
- `failed` → Red (all failed)
- `pending` → Blue (in progress)

## Next Steps

1. Implement notification router endpoints
2. Add authentication and authorization
3. Add rate limiting for bulk sends
4. Implement webhook handlers for delivery status
5. Add notification templates support
6. Create admin dashboard for monitoring

## Support

For Termii-specific issues:
- Documentation: https://developers.termii.com
- Support: support@termii.com
