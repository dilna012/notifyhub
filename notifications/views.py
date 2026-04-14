# notifications/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from datetime import timedelta, datetime
import json
import csv

from .models import Notification, ReadStatus
from .forms import NotificationForm
from accounts.models import User
from accounts.decorators import sender_required, role_required

def home_page(request):
    """Home page for the website"""
    
    # Get REAL statistics from database
    total_notifications = Notification.objects.filter(is_draft=False).count()
    total_students = User.objects.filter(role='student', is_active=True).count()
    total_teachers = User.objects.filter(role='teacher', is_active=True).count()
    total_staff = User.objects.filter(role='staff', is_active=True).count()
    total_users = total_teachers + total_staff
    
    # Calculate read rate (percentage of read notifications)
    total_read_statuses = ReadStatus.objects.count()
    total_read = ReadStatus.objects.filter(is_read=True).count()
    
    if total_read_statuses > 0:
        read_rate = int((total_read / total_read_statuses) * 100)
    else:
        read_rate = 0
    
    context = {
        'total_notifications': total_notifications,
        'total_students': total_students,
        'total_users': total_users,
        'read_rate': read_rate,
    }
    
    return render(request, 'home.html', context)
# ===== STUDENT PUBLIC VIEWS =====
def student_notifications(request):
    """Public page for students to view all notifications"""
    notifications = Notification.objects.filter(
        is_draft=False,
        send_to_students=True
    ).order_by('-created_at')
    
    return render(request, 'notifications/student_view.html', {
        'notifications': notifications
    })

@csrf_exempt
def set_student_reminder(request, pk):
    """API for students to set reminders without login"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(pk=pk, is_draft=False)
            data = json.loads(request.body)
            reminder_time = data.get('reminder_time')
            
            reminders = request.session.get('reminders', {})
            reminders[str(pk)] = reminder_time
            request.session['reminders'] = reminders
            
            return JsonResponse({
                'success': True,
                'message': 'Reminder set successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ===== NOTIFICATION LIST VIEW =====
@login_required
def notification_list(request):
    """View for users to see notifications"""
    if request.user.role == 'principal':
        # Principal sees all notifications they sent
        notifications = Notification.objects.filter(
            sender=request.user, 
            is_draft=False
        ).order_by('-created_at')
        return render(request, 'notifications/sent_list.html', {
            'notifications': notifications
        })
    
    elif request.user.role == 'teacher':
        # ===== UPDATED: Teacher sees both sent and received with filter support =====
        # 1. Notifications they sent (to students)
        sent_notifications = Notification.objects.filter(
            sender=request.user, 
            is_draft=False
        )
        
        # 2. Notifications they received (from Principal)
        received_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_teachers=True
        ).exclude(sender=request.user)
        
        # Get filter from URL
        filter_type = request.GET.get('filter', 'all')
        
        # Apply filter
        if filter_type == 'sent':
            all_notifications = sent_notifications
        elif filter_type == 'received':
            all_notifications = received_notifications
        elif filter_type == 'unread':
            # Get unread received notifications
            all_notifications = received_notifications
            # We'll filter by read status later
        else:  # 'all' or any other
            all_notifications = (sent_notifications | received_notifications).distinct()
        
        all_notifications = all_notifications.order_by('-published_at', '-updated_at', '-created_at')
        
        # Get read status for received notifications
        notifications_with_status = []
        for notification in all_notifications:
            if notification.sender == request.user:
                # Sent notifications
                notifications_with_status.append({
                    'notification': notification,
                    'is_read': None,
                    'read_at': None,
                    'reminder_time': None,
                    'is_sent': True
                })
            else:
                # Received notifications
                read_status, created = ReadStatus.objects.get_or_create(
                    user=request.user,
                    notification=notification
                )
                
                # For unread filter, only include unread notifications
                if filter_type == 'unread' and read_status.is_read:
                    continue
                    
                notifications_with_status.append({
                    'notification': notification,
                    'is_read': read_status.is_read,
                    'read_at': read_status.read_at,
                    'reminder_time': read_status.reminder_time,
                    'is_sent': False
                })
        
        return render(request, 'notifications/teacher_list.html', {
            'notifications': notifications_with_status,
            'current_filter': filter_type
        })
    
    elif request.user.role == 'staff':
        # Staff see notifications meant for them
        staff_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_staff=True
        ).order_by('-created_at')
        
        # Get or create read status for each notification
        notifications_with_status = []
        for notification in staff_notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            notifications_with_status.append({
                'notification': notification,
                'is_read': read_status.is_read,
                'read_at': read_status.read_at,
                'reminder_time': read_status.reminder_time
            })
        
        return render(request, 'notifications/notification_list.html', {
            'notifications': notifications_with_status
        })
    
    else:
        # Default for other roles
        return render(request, 'notifications/notification_list.html', {
            'notifications': []
        })

# ===== NOTIFICATION CREATE VIEW =====
@login_required
@sender_required
def notification_create(request):
    """View for teachers and principal to create notifications"""
    if request.method == 'POST':
        # Pass user to form
        form = NotificationForm(request.POST, user=request.user)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = request.user
            notification.save()
            
            # Check if it's a draft or publish
            if 'draft' in request.POST:
                notification.is_draft = True
                notification.save()
                messages.success(request, 'Draft saved successfully!')
                return redirect('draft_list')
            else:
                notification.is_draft = False
                notification.save()
                
                # Determine recipients based on selections
                recipients = User.objects.none()
                
                if request.user.role == 'principal':
                    # Principal can select specific groups
                    if form.cleaned_data.get('send_to_students'):
                        students = User.objects.filter(role='student', is_active=True)
                        recipients = recipients | students
                    
                    if form.cleaned_data.get('send_to_teachers'):
                        teachers = User.objects.filter(role='teacher', is_active=True)
                        recipients = recipients | teachers
                    
                    if form.cleaned_data.get('send_to_staff'):
                        staff = User.objects.filter(role='staff', is_active=True)
                        recipients = recipients | staff
                    
                    # Build success message
                    selected_groups = []
                    if form.cleaned_data.get('send_to_students'):
                        selected_groups.append('Students')
                    if form.cleaned_data.get('send_to_teachers'):
                        selected_groups.append('Teachers')
                    if form.cleaned_data.get('send_to_staff'):
                        selected_groups.append('Staff')
                    
                    group_text = ', '.join(selected_groups)
                    success_msg = f'Notification sent to: {group_text}'
                    
                else:  # Teacher
                    # Teachers only send to students
                    recipients = User.objects.filter(role='student', is_active=True)
                    success_msg = 'Notification sent to all students!'
                
                # Create ReadStatus entries for all recipients
                if recipients.exists():
                    read_statuses = [
                        ReadStatus(user=recipient, notification=notification)
                        for recipient in recipients
                    ]
                    ReadStatus.objects.bulk_create(read_statuses)
                    messages.success(request, success_msg)
                else:
                    messages.warning(request, 'No recipients selected! Notification saved but not sent.')
                
                return redirect('notification_list')
    else:
        # Pass user to form for GET request
        form = NotificationForm(user=request.user)
    
    return render(request, 'notifications/notification_create.html', {
        'form': form,
        'is_principal': request.user.role == 'principal'
    })

# ===== NOTIFICATION DETAIL VIEW =====
@login_required
def notification_detail(request, pk):
    """View notification details"""
    notification = get_object_or_404(Notification, pk=pk)
    
    # Check if user has permission to view this notification
    if request.user.role in ['staff', 'teacher']:  # Added teacher here
        if notification.is_draft:
            messages.error(request, "You cannot view draft notifications.")
            return redirect('notification_list')
            
        # Mark as read when viewed (for received notifications only)
        if notification.sender != request.user:
            read_status, created = ReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            if not read_status.is_read:
                read_status.mark_as_read()
                messages.info(request, "Notification marked as read.")
    
    # Get read status for this user
    user_read_status = None
    if request.user.role in ['staff', 'teacher'] and notification.sender != request.user:
        user_read_status = ReadStatus.objects.filter(
            user=request.user,
            notification=notification
        ).first()
    
    context = {
        'notification': notification,
        'user_read_status': user_read_status,
        'can_edit': request.user == notification.sender and notification.is_draft,
    }
    
    return render(request, 'notifications/notification_detail.html', context)

# ===== DRAFT LIST VIEW =====
@login_required
@sender_required
def draft_list(request):
    """View for teachers and principal to see their drafts"""
    drafts = Notification.objects.filter(
        sender=request.user,
        is_draft=True
    ).order_by('-updated_at')
    
    return render(request, 'notifications/draft_list.html', {'drafts': drafts})

# ===== NOTIFICATION STATS VIEW =====
@login_required
@sender_required
def notification_stats(request, pk):
    """View read statistics for a notification"""
    try:
        notification = get_object_or_404(Notification, pk=pk)
        
        # Check permission
        if request.user.role == 'teacher' and notification.sender != request.user:
            messages.error(request, "You can only view stats for your own notifications.")
            return redirect('notification_list')
        
        # Get read status
        read_statuses = ReadStatus.objects.filter(
            notification=notification
        ).select_related('user')
        
        total_students = User.objects.filter(role='student').count()
        read_count = read_statuses.filter(is_read=True).count()
        unread_count = read_statuses.filter(is_read=False).count()
        
        if total_students > 0:
            read_percentage = (read_count / total_students * 100)
            unread_percentage = (unread_count / total_students * 100)
        else:
            read_percentage = 0
            unread_percentage = 0
        
        read_user_ids = read_statuses.filter(is_read=True).values_list('user_id', flat=True)
        unread_students = User.objects.filter(
            role='student'
        ).exclude(
            id__in=read_user_ids
        )[:20]
        
        context = {
            'notification': notification,
            'read_statuses': read_statuses[:50],
            'total_students': total_students,
            'read_count': read_count,
            'unread_count': unread_count,
            'read_percentage': round(read_percentage, 1),
            'unread_percentage': round(unread_percentage, 1),
            'unread_students': unread_students,
        }
        
        return render(request, 'notifications/notification_stats.html', context)
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('notification_list')


# ===== ANALYTICS DASHBOARD =====
@login_required
def notification_dashboard(request):
    """Statistics dashboard for teachers and principal"""
    
    if request.user.role == 'principal':
        notifications = Notification.objects.filter(is_draft=False)
    else:
        notifications = Notification.objects.filter(sender=request.user, is_draft=False)
    
    # Recent activity
    recent_activity = ReadStatus.objects.filter(
        notification__in=notifications,
        is_read=True
    ).select_related('user', 'notification').order_by('-read_at')[:10]
    
    # Category stats
    category_stats = notifications.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Daily stats for last 7 days
    daily_stats = []
    for i in range(7):
        day = timezone.now() - timedelta(days=i)
        count = notifications.filter(
            created_at__date=day.date()
        ).count()
        daily_stats.append({
            'date': day.strftime('%A'),
            'count': count
        })
    
    # Read stats for each notification
    read_stats = []
    for notification in notifications.order_by('-created_at')[:10]:
        total_students = User.objects.filter(role='student').count()
        read_count = ReadStatus.objects.filter(
            notification=notification, 
            is_read=True
        ).count()
        read_stats.append({
            'id': notification.id,
            'title': notification.title,
            'category': notification.category,
            'get_category_display': notification.get_category_display(),
            'created_at': notification.created_at,
            'total_students': total_students,
            'read_count': read_count,
            'unread_count': total_students - read_count,
            'read_percentage': round((read_count / total_students * 100) if total_students > 0 else 0, 1)
        })
    
    context = {
        'total_notifications': notifications.count(),
        'category_stats': category_stats,
        'recent_activity': recent_activity,
        'daily_stats': daily_stats,
        'read_stats': read_stats,
        'is_principal': request.user.role == 'principal',
    }
    
    return render(request, 'notifications/dashboard_stats.html', context)
# ===== NOTIFICATION DELETE VIEW =====
@login_required
def notification_delete(request, pk):
    """Delete a notification - only the sender can delete"""
    notification = get_object_or_404(Notification, pk=pk)
    
    # Check if the logged-in user is the sender
    if request.user == notification.sender:
        notification_title = notification.title
        notification.delete()
        messages.success(request, f'Notification "{notification_title}" has been deleted successfully.')
    else:
        messages.error(request, 'You can only delete your own notifications.')
    
    # Redirect back to the page they came from
    return redirect('notification_list')

# ===== EXPORT STATS VIEW =====
@login_required
@sender_required
def export_stats(request, pk):
    """Export read statistics as CSV"""
    notification = get_object_or_404(Notification, pk=pk, sender=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{notification.title}_stats.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Email', 'Read Status', 'Read At', 'Reminder Set'])
    
    read_statuses = ReadStatus.objects.filter(notification=notification).select_related('user')
    for status in read_statuses:
        writer.writerow([
            status.user.username,
            status.user.email,
            'Read' if status.is_read else 'Unread',
            status.read_at,
            status.reminder_time
        ])
    
    return response

def unread_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})

@login_required
@sender_required
def edit_draft(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        sender=request.user
    )

    if request.method == 'POST':
        form = NotificationForm(request.POST, instance=notification, user=request.user)

        if form.is_valid():
            notification = form.save(commit=False)
            from django.utils import timezone

            if 'draft' in request.POST:
                notification.is_draft = True
                notification.updated_at = timezone.now()
                notification.save()

               # In notifications/views.py — replace set_reminder view

# In notifications/views.py — replace set_reminder view

@login_required
def set_reminder(request, pk):
    """Users can set reminders for notifications"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk)
        read_status, created = ReadStatus.objects.get_or_create(
            user=request.user,
            notification=notification
        )

        reminder_time = request.POST.get('reminder_time')
        if reminder_time:
            parsed_time = parse_datetime(reminder_time)

            # datetime-local often gives naive string like 2026-04-14T15:20
            if not parsed_time:
                try:
                    parsed_time = datetime.strptime(reminder_time, "%Y-%m-%dT%H:%M")
                except ValueError:
                    parsed_time = None

            if parsed_time:
                if timezone.is_naive(parsed_time):
                    parsed_time = timezone.make_aware(
                        parsed_time,
                        timezone.get_current_timezone()
                    )

                if parsed_time <= timezone.now():
                    messages.error(request, 'Reminder time must be in the future.')
                else:
                    read_status.reminder_time = parsed_time
                    read_status.reminder_sent = False
                    read_status.reminder_sent_at = None
                    read_status.save()

                    local_time = timezone.localtime(parsed_time)
                    messages.success(
                        request,
                        f'Reminder set for {local_time.strftime("%b %d, %Y at %I:%M %p")}!'
                    )
            else:
                messages.error(request, 'Invalid date/time format.')

    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))


    
@login_required
@sender_required
def publish_draft(request, pk):
    draft = get_object_or_404(
        Notification,
        pk=pk,
        sender=request.user,
        is_draft=True
    )

    if request.method == "POST":
        from django.utils import timezone

        draft.is_draft = False
        draft.published_at = timezone.now()
        draft.save()

        messages.success(request, "Notification published successfully!")
        return redirect("notification_list")

    return redirect("draft_list")
    