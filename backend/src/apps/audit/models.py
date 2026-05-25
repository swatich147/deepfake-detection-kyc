"""Audit models."""
from django.db import models


class AuditLog(models.Model):
    """Audit log for tracking API access."""
    
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        'users.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50, blank=True, null=True)
    resource_id = models.UUIDField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    request_method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=500)
    request_body = models.JSONField(null=True, blank=True)
    
    response_status = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.user_id} at {self.created_at}"
