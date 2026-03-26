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
]