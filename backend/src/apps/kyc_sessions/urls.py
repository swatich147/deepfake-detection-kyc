"""KYC Session URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KYCSessionViewSet

router = DefaultRouter()
router.register('', KYCSessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]
