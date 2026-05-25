"""KYC Session models."""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class KYCSession(models.Model):
    """KYC video verification session."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('recording', 'Recording'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('flagged', 'Flagged'),
        ('expired', 'Expired'),
    ]
    
    CHALLENGE_TYPES = [
        ('none', 'None'),
        ('random_movement', 'Random Movement'),
        ('read_text', 'Read Text'),
        ('blink', 'Blink Detection'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'users.Organization',
        on_delete=models.CASCADE,
        related_name='kyc_sessions'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sessions'
    )
    
    # Applicant info
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    applicant_name = models.CharField(max_length=255, blank=True, null=True)
    applicant_document_type = models.CharField(max_length=50, blank=True, null=True)
    applicant_document_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Session state
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Video info
    video_s3_key = models.CharField(max_length=500, blank=True, null=True)
    video_duration_ms = models.IntegerField(null=True, blank=True)
    video_resolution = models.CharField(max_length=20, blank=True, null=True)
    video_size_bytes = models.BigIntegerField(null=True, blank=True)
    
    # Challenge
    challenge_type = models.CharField(max_length=50, choices=CHALLENGE_TYPES, default='none')
    challenge_data = models.JSONField(default=dict, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'external_reference']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Session {self.id} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.KYC_SESSION_EXPIRY_MINUTES
            )
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at


class VideoChunk(models.Model):
    """Video chunk for streaming upload."""
    
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        KYCSession,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    chunk_index = models.IntegerField()
    s3_key = models.CharField(max_length=500)
    size_bytes = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'video_chunks'
        unique_together = ['session', 'chunk_index']
        ordering = ['chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} for {self.session_id}"
