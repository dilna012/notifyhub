# notifications/utils.py

from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_reminder_email(user, notification):
    """Send a reminder email to a user for a specific notification."""
    
    if not user.email:
        logger.warning(f"No email for user {user.username}, skipping reminder.")
        return False

    subject = f"⏰ Reminder: {notification.title}"

    plain_message = f"""
Hi {user.username},

This is a reminder for the following notification:

Title   : {notification.title}
Category: {notification.get_category_display()}
Message : {notification.message}

Please log in to view the full details.

— NotifyHub Team
"""

    html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #4a90e2;">⏰ Reminder: {notification.title}</h2>
        <p>Hi <strong>{user.username}</strong>,</p>
        <p>This is your scheduled reminder for:</p>
        <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #4a90e2; margin: 10px 0;">
            <strong>Category:</strong> {notification.get_category_display()}<br>
            <strong>Message:</strong><br>
            <p>{notification.message}</p>
        </div>
        <p style="color: #888; font-size: 12px;">— NotifyHub Team</p>
    </div>
</body>
</html>
"""

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Reminder email sent to {user.email} for '{notification.title}'")
        return True
    except Exception as e:
        logger.error(f"Failed to send reminder to {user.email}: {e}")
        return False