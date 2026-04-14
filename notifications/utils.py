# notifications/utils.py
from django.conf import settings
from django.core.mail import send_mail

def send_reminder_email(user, notification):
    if not user.email:
        return False

    subject = f"Reminder: {notification.title}"
    message = (
        f"Hello {user.username},\n\n"
        f"This is a reminder for the notification:\n\n"
        f"Title: {notification.title}\n"
        f"Message: {notification.message}\n\n"
        f"Please log in to the system to view more details."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return True