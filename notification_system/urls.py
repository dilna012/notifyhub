# notification_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views
from notifications import views as notifications_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', notifications_views.home_page, name='home'),
    path('accounts/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
    
    # Student public notifications
    path('student-notifications/', notifications_views.student_notifications, name='student_notifications'),
    
    # API endpoints
    path('unread-count/', notifications_views.unread_count, name='unread_count'),
    path('check-expired-pins/', notifications_views.check_expired_pins, name='check_expired_pins'),
    
    # Dashboard
    path('dashboard/', accounts_views.dashboard, name='dashboard'),
    
    # Profile
    path('profile/', accounts_views.profile_view, name='profile'),
    path('profile/edit/', accounts_views.edit_profile_view, name='edit_profile'),
    
    # User Management (Admin only)
    path('manage-users/', accounts_views.manage_users, name='manage_users'),
    path('add-user/', accounts_views.add_user, name='add_user'),
    path('edit-user/<int:user_id>/', accounts_views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', accounts_views.delete_user, name='delete_user'),
    
    # Password Reset
    path('forgot-password/', accounts_views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', accounts_views.verify_otp_view, name='verify_otp'),
    path('reset-password/', accounts_views.reset_password_view, name='reset_password'),
]

# ===== STEP 8: SERVE MEDIA FILES IN DEVELOPMENT =====
# This allows Django to serve uploaded files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Also serve static files (optional, but helpful)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)