"""
URL configuration for KYC project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', health_check, name='health'),
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/sessions/', include('apps.kyc_sessions.urls')),
    path('api/v1/analysis/', include('apps.analysis.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
