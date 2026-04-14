from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('create/', views.notification_create, name='notification_create'),
    path('drafts/', views.draft_list, name='draft_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('<int:pk>/stats/', views.notification_stats, name='notification_stats'),
    path('<int:pk>/set-reminder/', views.set_reminder, name='set_reminder'),
    path('student/', views.student_notifications, name='student_notifications'),
    path('student/set-reminder/<int:pk>/', views.set_student_reminder, name='set_student_reminder'),
    path('dashboard/', views.notification_dashboard, name='notification_dashboard'),
    path('<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    path('unread-count/', views.unread_count, name='unread_count'),
    path('draft/<int:pk>/edit/', views.edit_draft, name='edit_draft'),
    path('publish-draft/<int:pk>/', views.publish_draft, name='publish_draft'),
    path('reminders/create/', views.create_reminder, name='create_reminder'),
    path('reminders/', views.reminder_list, name='reminder_list'),
    path('reminders/my/', views.my_reminders, name='my_reminders'),
    path('reminders/<int:reminder_id>/', views.reminder_detail, name='reminder_detail'),
    path('reminders/<int:reminder_id>/send-now/', views.send_reminder_now, name='send_reminder_now'),
    path('profile-setup/step1/', views.profile_setup_step1, name='profile_setup_step1'),
    path('profile-setup/step2/', views.profile_setup_step2, name='profile_setup_step2'),
    path('profile-setup/step3/', views.profile_setup_step3, name='profile_setup_step3'),

]