from django.contrib import admin
from .models import Notification, ReadStatus

class ReadStatusInline(admin.TabularInline):
    model = ReadStatus
    extra = 0
    readonly_fields = ('read_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'sender', 'is_draft', 'event_date', 'created_at')
    list_filter = ('is_draft', 'sender__role', 'created_at')
    search_fields = ('title', 'message')
    inlines = [ReadStatusInline]
    
    def get_read_count_display(self, obj):
        return obj.get_read_count()
    get_read_count_display.short_description = 'Read Count'

@admin.register(ReadStatus)
class ReadStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification', 'is_read', 'read_at', 'reminder_time')
    list_filter = ('is_read', 'user__role')
    search_fields = ('user__username', 'notification__title')
