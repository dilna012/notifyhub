# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from notifications.models import Notification, ReadStatus
from .forms import LoginForm
from django.utils import timezone
import random
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ForgotPasswordForm, VerifyOTPForm, ResetPasswordForm
from django.contrib.auth import get_user_model
from .forms import ForgotPasswordForm, VerifyOTPForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .forms import ForgotPasswordForm
from .models import PasswordResetOTP

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
    profile_incomplete = (
        not user.email or 
        not user.first_name or 
        not user.last_name
    )   

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
            'profile_incomplete': profile_incomplete, 
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
            'profile_incomplete': profile_incomplete,
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
            'profile_incomplete': profile_incomplete,
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

# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import ProfileForm

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'user_obj': request.user
    })  

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)  # ✅ important
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']

            User = get_user_model()

            try:
                user = User.objects.get(
                    username=username,
                    is_active=True,
                    role__in=['principal', 'teacher', 'staff']
                )

                if not user.email:
                    messages.error(request, 'No email is linked to this account.')
                    return redirect('forgot_password')

                # Invalidate old unused OTPs for this user
                PasswordResetOTP.objects.filter(
                    user=user,
                    is_used=False
                ).update(is_used=True)

                code = f"{random.randint(100000, 999999)}"

                PasswordResetOTP.objects.create(
                    user=user,
                    code=code
                )

                send_mail(
                    subject='Your Password Reset Code',
                    message=(
                        f"Hello {user.username},\n\n"
                        f"Your password reset code is: {code}\n\n"
                        f"This code will expire in 10 minutes.\n"
                        f"If you did not request this, please ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                request.session['reset_user_id'] = user.id
                messages.success(request, 'A 6-digit code has been sent to your email.')
                return redirect('verify_otp')

            except User.DoesNotExist:
                messages.error(request, 'Invalid account details.')

    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})

def verify_otp_view(request):
    user_id = request.session.get('reset_user_id')

    if not user_id:
        messages.error(request, 'Password reset session expired. Please try again.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            otp = PasswordResetOTP.objects.filter(
                user_id=user_id,
                is_used=False
            ).order_by('-created_at').first()

            if not otp:
                messages.error(request, 'No valid reset code found. Please request a new one.')
                return redirect('forgot_password')

            if otp.is_expired():
                otp.is_used = True
                otp.save()
                messages.error(request, 'This code has expired. Please request a new one.')
                return redirect('forgot_password')

            otp.attempts += 1
            otp.save(update_fields=['attempts'])

            if otp.attempts > 5:
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                messages.error(request, 'Too many incorrect attempts. Please request a new code.')
                return redirect('forgot_password')

            if otp.code != code:
                messages.error(request, 'Invalid code.')
                return redirect('verify_otp')

            otp.is_used = True
            otp.save(update_fields=['is_used'])

            request.session['otp_verified'] = True
            messages.success(request, 'Code verified successfully.')
            return redirect('reset_password')

    else:
        form = VerifyOTPForm()

    return render(request, 'accounts/verify_otp.html', {'form': form})

def reset_password_view(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')

    if not user_id or not otp_verified:
        messages.error(request, 'Password reset session is invalid or expired.')
        return redirect('forgot_password')

    User = get_user_model()
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.save()

            # clear reset session
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)

            messages.success(request, 'Password reset successful. Please log in.')
            return redirect('login')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form})