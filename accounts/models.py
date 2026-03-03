from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('principal', '👑 Principal'),
        ('teacher', '👩‍🏫 Teacher'),
        ('staff', '🧑‍💼 Non-Teaching Staff'),
        ('student', '👨‍🎓 Student'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
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
