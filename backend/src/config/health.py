"""Health check for Docker and monitoring."""
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'service': 'deepfake-kyc-backend',
    })
