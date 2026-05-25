"""WebSocket URL routing."""
from django.urls import re_path
from .consumers import VideoStreamConsumer

websocket_urlpatterns = [
    re_path(r'ws/video-stream/(?P<session_id>[0-9a-f-]+)/$', VideoStreamConsumer.as_asgi()),
]
