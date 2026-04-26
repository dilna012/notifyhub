# notifications/forms.py
from django import forms
from .models import Notification

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'category', 'event_date', 'is_draft', 
                  'send_to_students', 'send_to_teachers', 'send_to_staff',
                  'attachment']  # Added attachment field
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
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx,.txt'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # IMPORTANT: Remove 'user' from kwargs before calling super()
        self.user = kwargs.pop('user', None)  # This line must come FIRST
        super().__init__(*args, **kwargs)     # Then call super() without 'user'
        
        self.fields['event_date'].required = False
        self.fields['is_draft'].label = "Save as draft"
        
        # Add attachment help text
        if self.fields.get('attachment'):
            self.fields['attachment'].help_text = "Supported: PDF, DOC, DOCX, JPG, PNG, XLS, XLSX (Max: 10MB)"
            self.fields['attachment'].required = False
        
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
    
    def clean_attachment(self):
        """Validate the attachment file"""
        attachment = self.cleaned_data.get('attachment')
        
        if attachment:
            # Check file size (10MB limit = 10 * 1024 * 1024 bytes)
            if attachment.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')
            
            # Check file extension
            import os
            ext = os.path.splitext(attachment.name)[1].lower()
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.xls', '.xlsx', '.txt']
            
            if ext not in allowed_extensions:
                raise forms.ValidationError(f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}')
        
        return attachment