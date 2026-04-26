# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import os

class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('academic', '📚 Academic'),
        ('exam', '📝 Examination'),
        ('event', '🎉 Event'),
        ('holiday', '🏖️ Holiday'),
        ('urgent', '⚠️ Urgent'),
        ('general', '📢 General'),
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    
    is_draft = models.BooleanField(default=True)
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    
    event_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Audience fields
    send_to_students = models.BooleanField(default=True)
    send_to_teachers = models.BooleanField(default=False)
    send_to_staff = models.BooleanField(default=False)
    
    # ===== NEW: File Attachment Field =====
    attachment = models.FileField(
        upload_to='notification_attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Upload PDF, Image, or Document (Max: 10MB)"
    )
    attachment_name = models.CharField(max_length=255, blank=True, null=True)
    attachment_size = models.IntegerField(default=0)  # Size in bytes
    
    class Meta:
        ordering = ['-published_at', '-created_at']
    
    def __str__(self):
        return self.title
    
    def display_time(self):
        return self.published_at or self.created_at
    
    def is_event_expired(self):
        """Check if the event date has passed"""
        if self.event_date:
            return self.event_date < timezone.now()
        return False
    
    def get_read_count(self):
        return self.readstatus_set.filter(is_read=True).count()
    
    def get_total_students(self):
        from accounts.models import User
        return User.objects.filter(role='student').count()
    
    def get_read_percentage(self):
        total = self.get_total_students()
        if total == 0:
            return 0
        return (self.get_read_count() / total) * 100
    
    def get_file_extension(self):
        if self.attachment:
            name, ext = os.path.splitext(self.attachment.name)
            return ext.lower()
        return ''
    
    def get_file_icon(self):
        ext = self.get_file_extension()
        icons = {
            '.pdf': 'fa-file-pdf',
            '.doc': 'fa-file-word',
            '.docx': 'fa-file-word',
            '.xls': 'fa-file-excel',
            '.xlsx': 'fa-file-excel',
            '.jpg': 'fa-file-image',
            '.jpeg': 'fa-file-image',
            '.png': 'fa-file-image',
            '.gif': 'fa-file-image',
            '.mp4': 'fa-file-video',
            '.mp3': 'fa-file-audio',
            '.zip': 'fa-file-archive',
            '.txt': 'fa-file-alt',
        }
        return icons.get(ext, 'fa-file')
class ReadStatus(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    reminder_time = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'notification']

    def __str__(self):
        return f"{self.user.username} - {self.notification.title}: {'Read' if self.is_read else 'Unread'}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()