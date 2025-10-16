# Email Notification System

## Overview

The STING Platform includes a comprehensive email notification system that sends automated notifications for document approvals, system alerts, and other important events. The system uses templated emails with STING's signature dark theme styling.

## Features

### ✅ Implemented
- Document approval notifications
- Document rejection notifications  
- Pending approval notifications for admins
- System alert notifications
- Beautiful HTML email templates with STING branding
- SMTP configuration support
- Mailpit integration for development

### 🔄 Configuration

The email service is configured via environment variables:

```env
# SMTP Configuration
SMTP_SERVER=localhost          # SMTP server hostname
SMTP_PORT=1025                # SMTP port (1025 for Mailpit)
SMTP_USERNAME=                # SMTP username (optional)
SMTP_PASSWORD=                # SMTP password (optional)
SMTP_USE_TLS=false           # Enable TLS (true/false)

# From Address Configuration
FROM_EMAIL=noreply@sting.local
FROM_NAME=STING Platform

# Base URL for email links
BASE_URL=https://localhost:8443
```

### 📧 Email Types

#### 1. Document Approval Notifications
Sent to document uploaders when their document is approved.

**Triggers:**
- Admin approves a pending document
- Document status changes from 'pending' to 'approved'

**Content:**
- Document name and honey jar
- Approver name and timestamp
- Success styling with green accent
- Link to dashboard

#### 2. Document Rejection Notifications  
Sent to document uploaders when their document is rejected.

**Triggers:**
- Admin rejects a pending document
- Document status changes from 'pending' to 'rejected'

**Content:**
- Document name and honey jar
- Reviewer name and timestamp
- Rejection reason/feedback
- Warning styling with yellow accent
- Link to dashboard for resubmission

#### 3. Pending Approval Notifications
Sent to admins when documents need review.

**Triggers:**
- New document uploaded by non-admin user
- Document status set to 'pending'

**Content:**
- Document name and honey jar
- Uploader name and timestamp  
- Count of total pending documents
- Link to admin panel for review

#### 4. System Alert Notifications
Sent to admins for system events and alerts.

**Triggers:**
- System errors or warnings
- Storage usage alerts
- Security events
- Manual admin alerts

**Content:**
- Alert type and severity level
- Detailed alert message
- Color-coded severity indicators
- Timestamp and dashboard link

### 🎨 Email Design

All emails use STING's signature styling:
- **Dark Theme**: Slate background with yellow accents
- **Responsive Design**: Works on desktop and mobile
- **STING Branding**: Yellow gradient headers with bee emoji
- **Status Colors**: Green (success), Yellow (warning), Red (error)
- **Grid Layout**: Two-column information displays

### 🔧 Usage

#### Basic Usage

```python
from app.services.email_service import get_email_service

email_service = get_email_service()

# Send approval notification
success = email_service.send_document_approval_notification(
    recipient_email='user@example.com',
    document_name='Security Policy v2.pdf',
    honey_jar_name='Security Documentation',
    approver_name='Admin User'
)
```

#### Advanced Usage

```python
# Send system alert
email_service.send_system_alert(
    admin_emails=['admin@sting.local'],
    alert_type='Storage Usage High',
    alert_message='Honey Reserve storage usage has exceeded 85%',
    severity='high'
)

# Send rejection with reason
email_service.send_document_rejection_notification(
    recipient_email='user@example.com',
    document_name='Draft Policy.pdf',
    honey_jar_name='Legal Documentation',
    reviewer_name='Legal Team',
    rejection_reason='Document needs compliance review before approval'
)
```

### 🛠️ Development Setup

#### Using Mailpit (Recommended)
Mailpit is included in the STING Docker Compose setup for email testing:

1. **View Emails**: http://localhost:8026
2. **SMTP Port**: 1025 (configured by default)
3. **No Authentication**: Required for local development

#### Using External SMTP
For production deployments:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=noreply@your-domain.com
```

### 🔍 Troubleshooting

#### Common Issues

1. **Emails Not Sending**
   - Check Mailpit is running: `docker ps | grep mailpit`
   - Verify SMTP configuration in environment variables
   - Check application logs for SMTP errors

2. **Template Rendering Errors**
   - Email templates use fallback HTML if files missing
   - Check Flask application context is available
   - Verify template variables are properly passed

3. **Missing Links in Emails**
   - Ensure `BASE_URL` environment variable is set correctly
   - Links use HTTPS by default for security

#### Debug Mode

Enable debug logging to troubleshoot email issues:

```python
import logging
logging.getLogger('app.services.email_service').setLevel(logging.DEBUG)
```

### 📈 Monitoring

The email service logs all sent messages:
- **Success**: `Email sent successfully to user@example.com`
- **Failure**: `Email send failed: connection refused`

Monitor email delivery through:
- Application logs
- Mailpit UI (development)
- SMTP provider dashboards (production)

### 🚀 Future Enhancements

- Email queuing for high-volume scenarios
- Template customization through admin panel
- User email preference management
- Weekly digest notifications
- Email open and click tracking
- Multi-language template support

### 📝 API Integration

The email service integrates with existing STING routes:
- Document approval/rejection in Admin Panel
- File upload workflows
- System monitoring and alerts
- User management operations

### 🔐 Security Considerations

- SMTP credentials stored as environment variables
- HTML email sanitization
- Rate limiting for alert notifications  
- No sensitive data in email subject lines
- Secure HTTPS links to dashboard