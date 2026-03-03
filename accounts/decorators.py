from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                if request.user.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard')
            else:
                return redirect('login')
        return wrapper
    return decorator

def sender_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.can_send_notifications:
            return view_func(request, *args, **kwargs)
        messages.error(request, "You don't have permission to send notifications.")
        return redirect('notification_list')
    return wrapper