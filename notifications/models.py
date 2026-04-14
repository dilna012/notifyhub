# notifications/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# ============================================
# NOTIFICATION MODEL
# ============================================

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

    send_to_students = models.BooleanField(default=True)
    send_to_teachers = models.BooleanField(default=False)
    send_to_staff = models.BooleanField(default=False)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def display_time(self):
        return self.published_at or self.created_at

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


# ============================================
# READ STATUS MODEL
# ============================================

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

    class Meta:
        unique_together = ['user', 'notification']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title}: {'Read' if self.is_read else 'Unread'}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


# ============================================
# USER PROFILE MODEL
# ============================================

class UserProfile(models.Model):
    USER_TYPES = [
        ('principal', 'Principal'),
        ('teacher', 'Teacher'),
        ('nonteaching', 'Non-Teaching Staff'),
        ('admin', 'Admin'),
        ('student', 'Student'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='userprofile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='teacher')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    is_profile_complete = models.BooleanField(default=False)
    completion_step = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


# Signal to create profile when user is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
    else:
        UserProfile.objects.create(user=instance)


# ============================================
# REMINDER MODEL
# ============================================

class Reminder(models.Model):
    REMINDER_TYPES = [
        ('meeting', 'Meeting'),
        ('assignment', 'Assignment'),
        ('exam', 'Exam'),
        ('event', 'Event'),
        ('deadline', 'Deadline'),
        ('general', 'General'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES, default='general')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Timing
    scheduled_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_recurring = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Relationships
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reminders')
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ReminderRecipient', related_name='received_reminders')
    
    # For specific groups
    send_to_all_teachers = models.BooleanField(default=False)
    send_to_all_students = models.BooleanField(default=False)
    send_to_all_nonteaching = models.BooleanField(default=False)
    send_to_principal = models.BooleanField(default=False)
    
    # Attachment (optional)
    attachment = models.FileField(upload_to='reminders/', null=True, blank=True)
    
    class Meta:
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f"{self.title} - {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
    
    def is_due(self):
        return self.scheduled_time <= timezone.now()
    
    def get_recipients_list(self):
        """Get all recipients for this reminder"""
        return self.recipients.all()


# ============================================
# REMINDER RECIPIENT MODEL
# ============================================

class ReminderRecipient(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['reminder', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.reminder.title}"