"""Development settings."""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Use local file storage for development
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Background thread processing instead of Celery/Redis
USE_BACKGROUND_THREADS = True
