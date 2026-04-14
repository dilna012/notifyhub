# notifications/management/commands/send_due_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import ReadStatus
from notifications.utils import send_reminder_email

class Command(BaseCommand):
    help = "Send reminder emails for due notifications"

    def handle(self, *args, **kwargs):
        now = timezone.now()

        due_reminders = ReadStatus.objects.filter(
            reminder_time__isnull=False,
            reminder_time__lte=now,
            reminder_sent=False
        ).select_related('user', 'notification')

        sent_count = 0

        for item in due_reminders:
            try:
                sent = send_reminder_email(item.user, item.notification)
                if sent:
                    item.reminder_sent = True
                    item.reminder_sent_at = now
                    item.save(update_fields=['reminder_sent', 'reminder_sent_at'])
                    sent_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed for {item.user.username}: {e}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Total reminder emails sent: {sent_count}"
        ))