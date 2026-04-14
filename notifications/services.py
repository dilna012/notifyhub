# services.py (create new file)
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class ReminderService:
    """Service class for handling reminder emails and notifications"""
    
    def send_reminder_emails(self, reminder):
        """Send reminder emails to all recipients"""
        sent_count = 0
        
        recipients = reminder.reminderrecipient_set.all()
        
        for recipient in recipients:
            # Check if user has completed profile and has email
            try:
                user_profile = recipient.user.userprofile
                if not user_profile.is_profile_complete or not user_profile.email:
                    continue
                
                # Send email
                success = self.send_single_reminder_email(
                    reminder=reminder,
                    recipient=recipient,
                    user_profile=user_profile
                )
                
                if success:
                    recipient.email_sent = True
                    recipient.email_sent_at = timezone.now()
                    recipient.save()
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"Error sending reminder to {recipient.user.username}: {str(e)}")
        
        # Update reminder status
        if sent_count > 0:
            reminder.email_sent = True
            reminder.email_sent_at = timezone.now()
            reminder.save()
        
        return sent_count
    
    def send_single_reminder_email(self, reminder, recipient, user_profile):
        """Send email to a single recipient"""
        try:
            subject = f"[{reminder.get_priority_display()}] {reminder.title}"
            
            # Prepare context for email template
            context = {
                'reminder': reminder,
                'recipient': recipient,
                'user_profile': user_profile,
                'reminder_type': reminder.get_reminder_type_display(),
                'priority': reminder.get_priority_display(),
                'priority_color': self.get_priority_color(reminder.priority),
                'site_name': 'School Management System',
                'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
            }
            
            # Render HTML email
            html_content = render_to_string('emails/reminder_email.html', context)
            text_content = strip_tags(html_content)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_profile.email],
                reply_to=[reminder.created_by.email] if reminder.created_by.email else None,
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Add attachment if exists
            if reminder.attachment:
                email.attach_file(reminder.attachment.path)
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Reminder email sent to {user_profile.email} for reminder '{reminder.title}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reminder email to {user_profile.email}: {str(e)}")
            return False
    
    def get_priority_color(self, priority):
        """Get color code for priority"""
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'urgent': '#dc3545',
        }
        return colors.get(priority, '#6c757d')
    
    def check_and_send_due_reminders(self):
        """Check for due reminders and send emails"""
        now = timezone.now()
        
        # Get reminders scheduled for now or within the last 5 minutes
        # that haven't been sent yet
        time_threshold = now - timedelta(minutes=5)
        
        due_reminders = Reminder.objects.filter(
            scheduled_time__lte=now,
            scheduled_time__gte=time_threshold,
            email_sent=False,
            status='pending'
        )
        
        total_sent = 0
        for reminder in due_reminders:
            sent_count = self.send_reminder_emails(reminder)
            if sent_count > 0:
                reminder.status = 'sent'
                reminder.save()
                total_sent += sent_count
        
        logger.info(f"Processed {due_reminders.count()} reminders, sent {total_sent} emails")
        return total_sent

    def send_reminder_summary(self):
        """Send daily summary of upcoming reminders"""
        tomorrow = timezone.now() + timedelta(days=1)
        
        # Get all users with completed profiles
        users = UserProfile.objects.filter(is_profile_complete=True)
        
        for user_profile in users:
            # Get tomorrow's reminders for this user
            upcoming_reminders = Reminder.objects.filter(
                recipients=user_profile.user,
                scheduled_time__date=tomorrow.date(),
                status='pending'
            )
            
            if upcoming_reminders.exists():
                self.send_summary_email(user_profile, upcoming_reminders)
    
    def send_summary_email(self, user_profile, reminders):
        """Send summary email for upcoming reminders"""
        subject = f"Reminder Summary for Tomorrow - {reminders.count()} reminders"
        
        context = {
            'user_profile': user_profile,
            'reminders': reminders,
            'date': timezone.now().date() + timedelta(days=1),
        }
        
        html_content = render_to_string('emails/reminder_summary.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_profile.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()