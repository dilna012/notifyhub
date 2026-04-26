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
from django.db.models import Count

from .models import Notification, ReadStatus
from .forms import NotificationForm
from accounts.models import User
from accounts.decorators import sender_required, role_required

def home_page(request):
    """Home page for the website with real statistics"""
    
    from accounts.models import User
    from .models import Notification
    
    total_notifications = Notification.objects.filter(is_draft=False).count()
    
    # Count ALL active users EXCLUDING admin
    total_users = User.objects.filter(is_active=True).exclude(role='admin').count()
    
    # Count teachers and staff
    total_teachers = User.objects.filter(role='teacher', is_active=True).count()
    total_staff = User.objects.filter(role='staff', is_active=True).count()
    total_faculty_staff = total_teachers + total_staff
    
    context = {
        'total_notifications': total_notifications,
        'total_users': total_users,
        'total_faculty_staff': total_faculty_staff,
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
        notifications = Notification.objects.filter(
            sender=request.user,
            is_draft=False
        ).order_by('-created_at')

        notifications_with_status = []
        for notification in notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            
            # ===== AUTO-UNPIN IF EVENT EXPIRED =====
            if read_status.is_pinned and notification.is_event_expired():
                read_status.is_pinned = False
                read_status.pinned_at = None
                read_status.save()
            
            notifications_with_status.append({
                'notification': notification,
                'reminder_time': read_status.reminder_time,
                'reminder_sent': read_status.reminder_sent,
                'is_pinned': read_status.is_pinned,
                'pinned_at': read_status.pinned_at,
                'has_attachment': bool(notification.attachment),  # Added
                'attachment_name': notification.attachment_name,  # Added
            })

        pinned = [item for item in notifications_with_status if item['is_pinned']]
        others = [item for item in notifications_with_status if not item['is_pinned']]
        notifications_with_status = pinned + others

        return render(request, 'notifications/sent_list.html', {
            'notifications': notifications_with_status,
            'now': timezone.now(),
        })

    elif request.user.role == 'teacher':
        sent_notifications = Notification.objects.filter(
            sender=request.user,
            is_draft=False
        )

        received_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_teachers=True
        ).exclude(sender=request.user)

        filter_type = request.GET.get('filter', 'all')

        if filter_type == 'sent':
            all_notifications = sent_notifications
        elif filter_type == 'received':
            all_notifications = received_notifications
        elif filter_type == 'unread':
            all_notifications = received_notifications
        else:
            all_notifications = (sent_notifications | received_notifications).distinct()

        all_notifications = all_notifications.order_by('-published_at', '-updated_at', '-created_at')

        notifications_with_status = []
        for notification in all_notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            
            # ===== AUTO-UNPIN IF EVENT EXPIRED =====
            if read_status.is_pinned and notification.is_event_expired():
                read_status.is_pinned = False
                read_status.pinned_at = None
                read_status.save()

            if notification.sender == request.user:
                notifications_with_status.append({
                    'notification': notification,
                    'is_read': None,
                    'read_at': None,
                    'reminder_time': read_status.reminder_time,
                    'reminder_sent': read_status.reminder_sent,
                    'is_pinned': read_status.is_pinned,
                    'pinned_at': read_status.pinned_at,
                    'is_sent': True,
                    'has_attachment': bool(notification.attachment),  # Added
                    'attachment_name': notification.attachment_name,  # Added
                })
            else:
                if filter_type == 'unread' and read_status.is_read:
                    continue

                notifications_with_status.append({
                    'notification': notification,
                    'is_read': read_status.is_read,
                    'read_at': read_status.read_at,
                    'reminder_time': read_status.reminder_time,
                    'reminder_sent': read_status.reminder_sent,
                    'is_pinned': read_status.is_pinned,
                    'pinned_at': read_status.pinned_at,
                    'is_sent': False,
                    'has_attachment': bool(notification.attachment),  # Added
                    'attachment_name': notification.attachment_name,  # Added
                })

        pinned = [item for item in notifications_with_status if item['is_pinned']]
        others = [item for item in notifications_with_status if not item['is_pinned']]
        notifications_with_status = pinned + others

        return render(request, 'notifications/teacher_list.html', {
            'notifications': notifications_with_status,
            'current_filter': filter_type,
            'now': timezone.now()
        })

    elif request.user.role == 'staff':
        staff_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_staff=True
        ).order_by('-created_at')

        notifications_with_status = []
        for notification in staff_notifications:
            read_status, created = ReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            
            # ===== AUTO-UNPIN IF EVENT EXPIRED =====
            if read_status.is_pinned and notification.is_event_expired():
                read_status.is_pinned = False
                read_status.pinned_at = None
                read_status.save()
            
            notifications_with_status.append({
                'notification': notification,
                'is_read': read_status.is_read,
                'read_at': read_status.read_at,
                'reminder_time': read_status.reminder_time,
                'reminder_sent': read_status.reminder_sent,
                'is_pinned': read_status.is_pinned,
                'pinned_at': read_status.pinned_at,
                'has_attachment': bool(notification.attachment),  # Added
                'attachment_name': notification.attachment_name,  # Added
            })

        pinned = [item for item in notifications_with_status if item['is_pinned']]
        others = [item for item in notifications_with_status if not item['is_pinned']]
        notifications_with_status = pinned + others

        return render(request, 'notifications/notification_list.html', {
            'notifications': notifications_with_status,
            'now': timezone.now(),
        })

    else:
        return render(request, 'notifications/notification_list.html', {
            'notifications': []
        })
        
# ===== NOTIFICATION CREATE VIEW (UPDATED WITH FILE UPLOAD) =====
@login_required
@sender_required
def notification_create(request):
    """View for teachers and principal to create notifications with file attachments"""
    if request.method == 'POST':
        # Pass user to form and include FILES for file upload
        form = NotificationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = request.user
            
            # ===== HANDLE FILE ATTACHMENT =====
            if request.FILES.get('attachment'):
                attachment = request.FILES['attachment']
                notification.attachment = attachment
                notification.attachment_name = attachment.name
                notification.attachment_size = attachment.size
            else:
                notification.attachment = None
                notification.attachment_name = None
                notification.attachment_size = 0
            
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
        'is_principal': request.user.role == 'principal',
        'now': timezone.now(),
    })

# ===== NOTIFICATION DETAIL VIEW (UPDATED WITH ATTACHMENT) =====
@login_required
def notification_detail(request, pk):
    """View notification details with attachment"""
    notification = get_object_or_404(Notification, pk=pk)
    
    # Check if user has permission to view this notification
    if request.user.role in ['staff', 'teacher']:
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
    """View read statistics - Only for notifications sent to Teachers/Staff"""
    try:
        notification = get_object_or_404(Notification, pk=pk)
        
        # Check permission
        if request.user.role == 'teacher' and notification.sender != request.user:
            messages.error(request, "You can only view stats for your own notifications.")
            return redirect('notification_list')
        
        # Check if notification was sent to teachers or staff
        if not notification.send_to_teachers and not notification.send_to_staff:
            messages.error(request, "Statistics are not available for student-only notifications.")
            return redirect('notification_detail', pk=pk)
        
        # Get all read statuses for this notification
        read_statuses = ReadStatus.objects.filter(
            notification=notification
        ).select_related('user')
        
        # Only get Teachers and Staff who have read (exclude Students)
        read_users = []
        for status in read_statuses.filter(is_read=True).order_by('-read_at'):
            if status.user.role in ['teacher', 'staff']:
                read_users.append({
                    'username': status.user.username,
                    'full_name': status.user.get_full_name(),
                    'email': status.user.email,
                    'role': status.user.get_role_display(),
                    'read_at': status.read_at,
                })
        
        read_count = len(read_users)
        
        context = {
            'notification': notification,
            'read_count': read_count,
            'read_users': read_users,
        }
        
        return render(request, 'notifications/notification_stats.html', context)
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('notification_list')

@login_required
def notification_dashboard(request):
    """Statistics dashboard for teachers and principal"""
    
    if request.user.role == 'principal':
        notifications = Notification.objects.filter(is_draft=False)
    else:
        notifications = Notification.objects.filter(sender=request.user, is_draft=False)
    
    # Get all notifications for the table
    all_notifications = notifications.order_by('-created_at')
    
    # Recent activity
    recent_activity = ReadStatus.objects.filter(
        notification__in=notifications,
        is_read=True
    ).select_related('user', 'notification').order_by('-read_at')[:10]
    
    # Category stats
    category_stats = notifications.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Read stats for each notification
    read_stats = []
    for notification in all_notifications[:50]:
        total_recipients = 0
        if notification.send_to_students:
            total_recipients += User.objects.filter(role='student', is_active=True).count()
        if notification.send_to_teachers:
            total_recipients += User.objects.filter(role='teacher', is_active=True).count()
        if notification.send_to_staff:
            total_recipients += User.objects.filter(role='staff', is_active=True).count()
        
        read_count = ReadStatus.objects.filter(
            notification=notification, 
            is_read=True
        ).count()
        
        read_percentage = round((read_count / total_recipients * 100), 1) if total_recipients > 0 else 0
        
        read_stats.append({
            'id': notification.id,
            'title': notification.title,
            'category': notification.category,
            'get_category_display': notification.get_category_display(),
            'created_at': notification.created_at,
            'read_count': read_count,
            'read_percentage': read_percentage,
        })
    
    context = {
        'total_notifications': notifications.count(),
        'category_stats': category_stats,
        'recent_activity': recent_activity,
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
        # Also delete the attachment file if exists
        if notification.attachment:
            notification.attachment.delete(save=False)
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
        form = NotificationForm(request.POST, request.FILES, instance=notification, user=request.user)

        if form.is_valid():
            notification = form.save(commit=False)
            
            # Handle attachment update
            if request.FILES.get('attachment'):
                # Delete old attachment if exists
                if notification.attachment:
                    notification.attachment.delete(save=False)
                attachment = request.FILES['attachment']
                notification.attachment = attachment
                notification.attachment_name = attachment.name
                notification.attachment_size = attachment.size
            
            from django.utils import timezone

            if 'draft' in request.POST:
                notification.is_draft = True
                notification.updated_at = timezone.now()
                notification.save()

    return redirect('draft_list')

@login_required
def set_reminder(request, pk):
    if not request.user.email:
        messages.error(request, 'Please add your email in your profile before setting reminders.')
        return redirect('profile')

    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk)

        if notification.event_date and notification.event_date <= timezone.now():
            messages.error(request, 'You cannot set a reminder because the event time has already passed.')
            return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

        read_status, created = ReadStatus.objects.get_or_create(
            user=request.user,
            notification=notification
        )

        reminder_time = request.POST.get('reminder_time')

        if reminder_time:
            try:
                naive_dt = datetime.strptime(reminder_time, "%Y-%m-%dT%H:%M")
            except ValueError:
                messages.error(request, 'Invalid date/time format.')
                return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

            aware_dt = timezone.make_aware(
                naive_dt,
                timezone.get_current_timezone()
            )

            if aware_dt <= timezone.now():
                messages.error(request, 'Reminder time must be in the future.')
                return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

            if notification.event_date and aware_dt > notification.event_date:
                messages.error(request, 'Reminder time must be before the event time.')
                return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

            read_status.reminder_time = aware_dt
            read_status.reminder_sent = False
            read_status.reminder_sent_at = None
            read_status.save()

            local_time = timezone.localtime(aware_dt)
            messages.success(
                request,
                f'Reminder set for {local_time.strftime("%b %d, %Y at %I:%M %p")}!'
            )

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
        
        # Create ReadStatus entries for recipients when publishing
        recipients = User.objects.none()
        if draft.send_to_students:
            recipients = recipients | User.objects.filter(role='student', is_active=True)
        if draft.send_to_teachers:
            recipients = recipients | User.objects.filter(role='teacher', is_active=True)
        if draft.send_to_staff:
            recipients = recipients | User.objects.filter(role='staff', is_active=True)
        
        if recipients.exists():
            existing_read_statuses = ReadStatus.objects.filter(
                notification=draft,
                user__in=recipients
            )
            existing_users = set(existing_read_statuses.values_list('user', flat=True))
            
            new_recipients = [user for user in recipients if user.id not in existing_users]
            if new_recipients:
                read_statuses = [
                    ReadStatus(user=recipient, notification=draft)
                    for recipient in new_recipients
                ]
                ReadStatus.objects.bulk_create(read_statuses)

        messages.success(request, "Notification published successfully!")
        return redirect("notification_list")

    return redirect("draft_list")

@login_required
def toggle_pin_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    
    # ===== CHECK IF EVENT HAS EXPIRED BEFORE PINNING =====
    if notification.is_event_expired():
        messages.warning(request, f'Cannot pin "{notification.title}" because the event date has passed.')
        return redirect(request.META.get('HTTP_REFERER', 'notification_list'))
    
    read_status, created = ReadStatus.objects.get_or_create(
        user=request.user,
        notification=notification
    )

    if read_status.is_pinned:
        read_status.is_pinned = False
        read_status.pinned_at = None
        messages.success(request, "Notification unpinned.")
    else:
        read_status.is_pinned = True
        read_status.pinned_at = timezone.now()
        messages.success(request, "Notification pinned.")

    read_status.save()
    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))

# ===== API: CHECK EXPIRED PINS =====
@login_required
def check_expired_pins(request):
    """API endpoint to check and unpin expired notifications"""
    from django.utils import timezone
    
    # Get all pinned notifications for the user where event has expired
    pinned_statuses = ReadStatus.objects.filter(
        user=request.user,
        is_pinned=True,
        notification__event_date__isnull=False,
        notification__event_date__lt=timezone.now()
    )
    
    unpinned_count = pinned_statuses.count()
    
    # Unpin them
    for status in pinned_statuses:
        status.is_pinned = False
        status.pinned_at = None
        status.save()
    
    return JsonResponse({'unpinned_count': unpinned_count})

# ===== NEW: AUTO-REFRESH NOTIFICATIONS API =====
@login_required
def latest_notifications_api(request):
    """API endpoint to get latest notifications without page refresh"""
    
    # Get last check timestamp from request
    last_check = request.GET.get('last_check')
    if last_check:
        try:
            last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        except:
            last_check = timezone.now() - timedelta(minutes=5)
    else:
        last_check = timezone.now() - timedelta(minutes=5)
    
    # Get new notifications based on user role
    if request.user.role == 'staff':
        new_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_staff=True,
            created_at__gt=last_check
        ).order_by('-created_at')
        
    elif request.user.role == 'student':
        new_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_students=True,
            created_at__gt=last_check
        ).order_by('-created_at')
        
    elif request.user.role == 'teacher':
        sent_notifications = Notification.objects.filter(
            sender=request.user,
            is_draft=False,
            created_at__gt=last_check
        )
        received_notifications = Notification.objects.filter(
            is_draft=False,
            send_to_teachers=True,
            created_at__gt=last_check
        ).exclude(sender=request.user)
        new_notifications = (sent_notifications | received_notifications).distinct().order_by('-created_at')
        
    elif request.user.role == 'principal':
        new_notifications = Notification.objects.filter(
            sender=request.user,
            is_draft=False,
            created_at__gt=last_check
        ).order_by('-created_at')
    else:
        new_notifications = []
    
    # Get count and prepare HTML
    new_count = new_notifications.count()
    
    # Build HTML for new notifications
    html = ''
    for notification in new_notifications:
        read_status = ReadStatus.objects.filter(
            user=request.user,
            notification=notification
        ).first()
        
        is_read = read_status.is_read if read_status else False
        
        html += f'''
        <div class="notification-item" data-category="{notification.category}">
            <div class="notification-card new-notification" style="border-left: 4px solid #fbbf24; background: #fffbeb;">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <span class="category-badge category-{notification.category}">
                            <i class="fas fa-tag"></i> {notification.get_category_display()}
                        </span>
                        <h5 class="mt-2 mb-2">
                            <i class="fas fa-bell text-primary"></i> {notification.title}
                        </h5>
                        <p class="text-muted">{notification.message|truncatechars:150}</p>
                        <div class="d-flex gap-3 mt-2">
                            <small><i class="fas fa-user"></i> {notification.sender.get_role_display()}</small>
                            <small><i class="fas fa-clock"></i> {notification.created_at|date:"M d, Y h:i A"}</small>
                        </div>
                        <div class="mt-3">
                            <a href="/notifications/detail/{notification.id}/" class="btn btn-sm btn-primary">
                                <i class="fas fa-eye"></i> View Details
                            </a>
                        </div>
                    </div>
                    <span class="badge {'bg-secondary' if is_read else 'bg-danger'}">
                        {'Read' if is_read else 'New'}
                    </span>
                </div>
            </div>
        </div>
        '''
    
    return JsonResponse({
        'new_count': new_count,
        'html': html,
        'timestamp': timezone.now().isoformat(),
        'has_new': new_count > 0
    })