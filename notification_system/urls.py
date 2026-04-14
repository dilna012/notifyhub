from django.contrib import admin
from django.urls import path, include
from notifications.views import home_page

# ✅ ADD THESE
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home_page, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
]

# ✅ MEDIA serving
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)