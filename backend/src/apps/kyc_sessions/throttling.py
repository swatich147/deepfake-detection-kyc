"""API rate limits (Phase 3)."""
from rest_framework.throttling import UserRateThrottle


class SessionCreateThrottle(UserRateThrottle):
    scope = 'session_create'


class AnalysisExportThrottle(UserRateThrottle):
    scope = 'export'
