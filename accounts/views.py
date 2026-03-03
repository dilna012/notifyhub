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
    
    if user.role in ['principal', 'teacher']:
        # Sender dashboard
        drafts = Notification.objects.filter(sender=user, is_draft=True).count()
        total_sent = Notification.objects.filter(sender=user, is_draft=False).count()
        recent_notifications = Notification.objects.filter(sender=user, is_draft=False).order_by('-created_at')[:5]
        
        context = {
            'drafts_count': drafts,
            'total_sent': total_sent,
            'recent_notifications': recent_notifications,
        }
        return render(request, 'accounts/dashboard.html', context)
    
    elif user.role == 'staff':
        # Staff dashboard
        # Get all notifications meant for staff
        all_staff_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_staff=True
        ).order_by('-created_at')
        
        # Create or get read status for each notification
        notifications_with_status = []
        unread_count = 0
        
        for notification in all_staff_notifications:
            # Get or create read status for this notification
            read_status, created = ReadStatus.objects.get_or_create(
                user=user,
                notification=notification,
                defaults={'is_read': False}
            )
            
            # Count unread
            if not read_status.is_read:
                unread_count += 1
            
            # Add to list with status
            notifications_with_status.append({
                'notification': notification,
                'is_read': read_status.is_read,
                'read_at': read_status.read_at,
                'reminder_time': read_status.reminder_time
            })
        
        # Total notifications count
        total_notifications = len(notifications_with_status)
        
        # Recent notifications (last 5)
        recent_notifications = notifications_with_status[:5]
        
        context = {
            'unread_count': unread_count,
            'total_notifications': total_notifications,
            'recent_notifications': recent_notifications,
            'all_notifications': notifications_with_status,
        }
        return render(request, 'accounts/dashboard.html', context)
    
    else:
        # Fallback for other roles (students shouldn't reach here)
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