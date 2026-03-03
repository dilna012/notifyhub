# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    # Add this CATEGORY_CHOICES at the top of the class
    CATEGORY_CHOICES = (
        ('academic', '📚 Academic'),
        ('exam', '📝 Examination'),
        ('event', '🎉 Event'),
        ('holiday', '🏖️ Holiday'),
        ('urgent', '⚠️ Urgent'),
        ('general', '📢 General'),
    )
    
    # Your existing fields
    title = models.CharField(max_length=200)
    message = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    is_draft = models.BooleanField(default=False)
    event_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ADD THIS NEW FIELD
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='general'
    )
    send_to_students = models.BooleanField(default=True)
    send_to_teachers = models.BooleanField(default=False)
    send_to_staff = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
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
    
    class Meta:
        unique_together = ['user', 'notification']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title}: {'Read' if self.is_read else 'Unread'}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()