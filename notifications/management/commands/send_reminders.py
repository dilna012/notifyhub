# notifications/management/commands/send_reminders.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import ReadStatus
from notifications.utils import send_reminder_email


class Command(BaseCommand):
    help = 'Send reminder emails for due reminders'

    def handle(self, *args, **kwargs):
        now = timezone.now()

        # Find all reminders that are due and haven't been sent yet
        due_reminders = ReadStatus.objects.filter(
            reminder_time__lte=now,
            reminder_sent=False,
            reminder_time__isnull=False,
        ).select_related('user', 'notification')

        count = 0
        for status in due_reminders:
            success = send_reminder_email(status.user, status.notification)
            if success:
                status.reminder_sent = True
                status.save(update_fields=['reminder_sent'])
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Sent to {status.user.email} — '{status.notification.title}'"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ✗ Failed for {status.user.email}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f'\nDone. {count} reminder(s) sent.'))

# management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from your_app.services import ReminderService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send scheduled reminders via email'

    def handle(self, *args, **options):
        service = ReminderService()
        
        self.stdout.write('Checking for due reminders...')
        sent_count = service.check_and_send_due_reminders()
        
        if sent_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {sent_count} reminder emails')
            )
        else:
            self.stdout.write('No reminders to send at this time.')