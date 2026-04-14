# notifications/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt_urls = [
                reverse('profile_setup_step1'),
                reverse('profile_setup_step2'),
                reverse('profile_setup_step3'),
                reverse('logout'),
                reverse('login'),
                '/admin/',
                '/media/',
                '/static/',
            ]
            
            if not any(request.path.startswith(url) for url in exempt_urls):
                try:
                    profile = request.user.userprofile
                    # Skip for students and admin (or adjust as needed)
                    if not profile.is_profile_complete and profile.user_type not in ['student']:
                        messages.info(request, 'Please complete your profile setup to continue.')
                        return redirect('profile_setup_step1')
                except:
                    pass
        
        response = self.get_response(request)
        return response