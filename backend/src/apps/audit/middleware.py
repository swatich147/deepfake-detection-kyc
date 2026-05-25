"""Audit middleware for logging API requests."""
import json
import time
import logging
import re
from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """Middleware to audit API requests."""
    
    AUDIT_PATHS = ['/api/v1/sessions/', '/api/v1/analysis/']
    SENSITIVE_FIELDS = ['password', 'token', 'secret', 'api_key', 'api_secret']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Only audit API paths
        if any(request.path.startswith(p) for p in self.AUDIT_PATHS):
            try:
                self._create_audit_log(request, response, start_time)
            except Exception as e:
                logger.error(f"Error creating audit log: {e}")
        
        return response
    
    def _create_audit_log(self, request, response, start_time):
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        
        # Parse request body
        body = None
        if request.body:
            try:
                body = json.loads(request.body)
                body = self._sanitize_body(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = None
        
        AuditLog.objects.create(
            organization_id=getattr(user, 'organization_id', None) if user else None,
            user_id=getattr(user, 'id', None) if user else None,
            action=f'{request.method}:{self._extract_action(request.path)}',
            resource_type=self._extract_resource_type(request.path),
            resource_id=self._extract_resource_id(request.path),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            request_method=request.method,
            request_path=request.path[:500],
            request_body=body,
            response_status=response.status_code,
            response_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _sanitize_body(self, data):
        """Remove sensitive fields from request body."""
        if isinstance(data, dict):
            return {
                k: '***REDACTED***' if k.lower() in self.SENSITIVE_FIELDS else self._sanitize_body(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_body(item) for item in data]
        return data
    
    def _get_client_ip(self, request):
        """Get client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def _extract_action(self, path):
        """Extract action name from path."""
        parts = path.strip('/').split('/')
        if len(parts) >= 3:
            return parts[2]
        return 'unknown'
    
    def _extract_resource_type(self, path):
        """Extract resource type from path."""
        if '/sessions/' in path:
            return 'kyc_session'
        elif '/analysis/' in path:
            return 'analysis'
        elif '/auth/' in path:
            return 'auth'
        return None
    
    def _extract_resource_id(self, path):
        """Extract UUID resource ID from path."""
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, path, re.IGNORECASE)
        if match:
            return match.group()
        return None
