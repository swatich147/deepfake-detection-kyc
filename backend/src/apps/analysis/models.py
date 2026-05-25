"""Analysis models."""
import uuid
from django.db import models


class AnalysisResult(models.Model):
    """Deepfake analysis result for a KYC session."""
    
    VERDICT_CHOICES = [
        ('genuine', 'Genuine'),
        ('suspicious', 'Suspicious'),
        ('fake', 'Fake'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        'kyc_sessions.KYCSession',
        on_delete=models.CASCADE,
        related_name='analysis_result'
    )
    
    # Scores (0.0 to 1.0, higher = more likely fake)
    overall_score = models.DecimalField(max_digits=5, decimal_places=4)
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES)
    
    # Individual model scores
    face_manipulation_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    face_manipulation_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    lipsync_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    lipsync_offset_ms = models.IntegerField(null=True, blank=True)
    rppg_quality = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    rppg_heart_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    av_correlation_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    frame_consistency_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    
    # Processing metadata
    faces_detected = models.IntegerField(default=0)
    frames_analyzed = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    model_versions = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analysis_results'

    def __str__(self):
        return f"Analysis {self.id} - {self.verdict} ({self.overall_score})"


class FrameScore(models.Model):
    """Per-frame analysis scores."""
    
    id = models.BigAutoField(primary_key=True)
    result = models.ForeignKey(
        AnalysisResult,
        on_delete=models.CASCADE,
        related_name='frame_scores'
    )
    frame_number = models.IntegerField()
    timestamp_ms = models.IntegerField()
    
    face_detected = models.BooleanField(default=False)
    face_bbox = models.JSONField(null=True, blank=True)
    face_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    manipulation_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    is_anomaly = models.BooleanField(default=False)
    heatmap_s3_key = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'frame_scores'
        ordering = ['frame_number']
        indexes = [
            models.Index(fields=['result', 'frame_number']),
        ]

    def __str__(self):
        return f"Frame {self.frame_number} - {self.manipulation_score}"
