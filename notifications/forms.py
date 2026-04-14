# notifications/forms.py
from django import forms
from .models import Notification

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'category', 'event_date', 'is_draft', 
                  'send_to_students', 'send_to_teachers', 'send_to_staff']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter notification title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': 'Enter notification message'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'event_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'is_draft': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'send_to_students': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'send_to_teachers': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'send_to_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # IMPORTANT: Remove 'user' from kwargs before calling super()
        self.user = kwargs.pop('user', None)  # This line must come FIRST
        super().__init__(*args, **kwargs)     # Then call super() without 'user'
        
        self.fields['event_date'].required = False
        self.fields['is_draft'].label = "Save as draft"
        
        # Customize based on user role - only if user exists
        if self.user:
            if self.user.role == 'teacher':
                # Teachers can only send to students
                self.fields['send_to_students'].initial = True
                self.fields['send_to_students'].disabled = True
                # Hide teacher and staff options for teachers
                self.fields['send_to_teachers'].widget = forms.HiddenInput()
                self.fields['send_to_staff'].widget = forms.HiddenInput()
                # Set labels
                self.fields['send_to_students'].label = "Send to Students (fixed)"
                
            elif self.user.role == 'principal':
                # Principal can choose all options
                self.fields['send_to_students'].label = "Send to Students"
                self.fields['send_to_teachers'].label = "Send to Teachers"
                self.fields['send_to_staff'].label = "Send to Staff"
                self.fields['send_to_students'].initial = True
                self.fields['send_to_teachers'].initial = False
                self.fields['send_to_staff'].initial = False

# forms.py (add to existing forms)
from django import forms
from .models import Reminder, UserProfile
from django.contrib.auth import get_user_model 
User = get_user_model() 
class ReminderForm(forms.ModelForm):
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    scheduled_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'reminder_type', 'priority',
            'send_to_all_teachers', 'send_to_all_students', 
            'send_to_all_nonteaching', 'send_to_principal',
            'attachment'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'reminder_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'send_to_all_teachers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_to_all_students': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_to_all_nonteaching': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_to_principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')
        
        if scheduled_date and scheduled_time:
            from datetime import datetime
            cleaned_data['scheduled_time'] = datetime.combine(scheduled_date, scheduled_time)
        
        return cleaned_data

class IndividualReminderForm(forms.ModelForm):
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    scheduled_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        required=True
    )
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'reminder_type', 'priority',
            'recipients', 'attachment'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'reminder_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

# Add to notifications/forms.py

class ProfileSetupStep1Form(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

class ProfileSetupStep2Form(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email for notifications'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UserProfile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email