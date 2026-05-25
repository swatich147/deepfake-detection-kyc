"""Zero-cost demo settings — SQLite, in-memory channels, local file storage."""
from pathlib import Path

from .development import *

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(BASE_DIR) / 'db' / 'demo.sqlite3',
    }
}

# Always in-memory WebSocket layer (no Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Run video analysis in a background thread instead of Celery
USE_BACKGROUND_THREADS = True

# Skip AWS entirely for demo
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
