# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from notifications.models import Notification, ReadStatus
from .forms import LoginForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user

    if user.role == 'principal':
        drafts = Notification.objects.filter(sender=user, is_draft=True).count()
        total_sent = Notification.objects.filter(sender=user, is_draft=False).count()
        recent_notifications = Notification.objects.filter(
            sender=user,
            is_draft=False
        ).order_by('-created_at')[:5]

        context = {
            'drafts_count': drafts,
            'total_sent': total_sent,
            'recent_notifications': recent_notifications,
            'is_principal': True,
        }
        return render(request, 'accounts/dashboard.html', context)

    elif user.role == 'teacher':
        sent_notifications = Notification.objects.filter(
            sender=user,
            is_draft=False
        ).order_by('-created_at')

        received_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_teachers=True
        ).exclude(sender=user).order_by('-created_at')

        received_with_status = []
        unread_count = 0

        for notification in received_notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=user,
                notification=notification,
                defaults={'is_read': False}
            )

            if not read_status.is_read:
                unread_count += 1

            received_with_status.append({
                'notification': notification,
                'is_read': read_status.is_read,
                'read_at': read_status.read_at,
                'reminder_time': read_status.reminder_time,
                'is_sent': False,
            })

        all_notifications = []

        for notification in sent_notifications:
            all_notifications.append({
                'notification': notification,
                'is_sent': True,
                'is_read': None,
                'read_at': None,
                'reminder_time': None,
            })

        for item in received_with_status:
            all_notifications.append(item)

        all_notifications.sort(
            key=lambda x: x['notification'].created_at,
            reverse=True
        )
        recent_notifications = all_notifications[:5]

        drafts = Notification.objects.filter(sender=user, is_draft=True).count()

        context = {
            'drafts_count': drafts,
            'total_sent': sent_notifications.count(),
            'total_received': received_notifications.count(),
            'unread_count': unread_count,
            'recent_notifications': recent_notifications,
            'received_notifications': received_with_status[:5],
            'is_teacher': True,
        }
        return render(request, 'accounts/dashboard.html', context)

    elif user.role == 'staff':
        staff_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_staff=True
        ).order_by('-created_at')

        notifications_with_status = []
        unread_count = 0

        for notification in staff_notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=user,
                notification=notification,
                defaults={'is_read': False}
            )

            if not read_status.is_read:
                unread_count += 1

            notifications_with_status.append({
                'notification': notification,
                'is_read': read_status.is_read,
                'read_at': read_status.read_at,
                'reminder_time': read_status.reminder_time,
            })

        total_notifications = len(notifications_with_status)
        recent_notifications = notifications_with_status[:5]

        context = {
            'unread_count': unread_count,
            'total_notifications': total_notifications,
            'recent_notifications': recent_notifications,
            'all_notifications': notifications_with_status,
            'is_staff': True,
        }
        return render(request, 'accounts/dashboard.html', context)

    else:
        context = {
            'unread_count': 0,
            'total_notifications': 0,
            'recent_notifications': [],
        }
        return render(request, 'accounts/dashboard.html', context)

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')
