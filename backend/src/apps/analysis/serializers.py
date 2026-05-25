"""Analysis serializers."""
from rest_framework import serializers
from .models import AnalysisResult, FrameScore


class FrameScoreSerializer(serializers.ModelSerializer):
    """Frame score serializer."""
    
    class Meta:
        model = FrameScore
        fields = [
            'frame_number',
            'timestamp_ms',
            'face_detected',
            'face_bbox',
            'face_confidence',
            'manipulation_score',
            'is_anomaly',
            'heatmap_s3_key',
        ]


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Analysis result serializer."""
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id',
            'overall_score',
            'verdict',
            'face_manipulation_score',
            'face_manipulation_confidence',
            'lipsync_score',
            'lipsync_offset_ms',
            'rppg_quality',
            'rppg_heart_rate',
            'av_correlation_score',
            'frame_consistency_score',
            'faces_detected',
            'frames_analyzed',
            'processing_time_ms',
            'model_versions',
            'created_at',
        ]


class AnalysisResultDetailSerializer(AnalysisResultSerializer):
    """Detailed analysis result with frame scores."""
    frame_scores = FrameScoreSerializer(many=True, read_only=True)
    
    class Meta(AnalysisResultSerializer.Meta):
        fields = AnalysisResultSerializer.Meta.fields + ['frame_scores']
