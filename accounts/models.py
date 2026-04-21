from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', '🔧 Admin'),  
        ('principal', '👑 Principal'),
        ('teacher', '👩‍🏫 Teacher'),
        ('staff', '🧑‍💼 Non-Teaching Staff'),
        ('student', '👨‍🎓 Student'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def can_send_notifications(self):
        return self.role in ['principal', 'teacher']
    
    @property
    def can_save_drafts(self):
        return self.role in ['principal', 'teacher']
    
    @property
    def can_view_read_counts(self):
        return self.role in ['principal', 'teacher']

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.username} - {self.code}"
