from django.contrib import admin
from .models import User

# Register your custom user model so admin can manage it
admin.site.register(User)