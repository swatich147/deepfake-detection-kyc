"""KYC Session serializers."""
from rest_framework import serializers
from .models import KYCSession, VideoChunk


class VideoChunkSerializer(serializers.ModelSerializer):
    """Video chunk serializer."""
    
    class Meta:
        model = VideoChunk
        fields = ['id', 'chunk_index', 's3_key', 'size_bytes', 'duration_ms', 'created_at']


class KYCSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating KYC sessions."""
    
    class Meta:
        model = KYCSession
        fields = [
            'external_reference',
            'applicant_name',
            'applicant_document_type',
            'applicant_document_number',
            'challenge_type',
            'metadata',
        ]

    def validate_external_reference(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError('Reference too long')
        return value

    def validate_applicant_name(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError('Name too long')
        return value

    def validate_challenge_type(self, value):
        allowed = {c[0] for c in KYCSession.CHALLENGE_TYPES}
        if value not in allowed:
            raise serializers.ValidationError(f'Invalid challenge type. Choose: {", ".join(sorted(allowed))}')
        return value


class KYCSessionSerializer(serializers.ModelSerializer):
    """KYC Session serializer."""
    websocket_url = serializers.SerializerMethodField()
    challenge = serializers.SerializerMethodField()
    analysis = serializers.SerializerMethodField()
    
    class Meta:
        model = KYCSession
        fields = [
            'id',
            'external_reference',
            'applicant_name',
            'applicant_document_type',
            'applicant_document_number',
            'status',
            'video_duration_ms',
            'video_resolution',
            'challenge_type',
            'challenge_data',
            'challenge',
            'websocket_url',
            'analysis',
            'expires_at',
            'created_at',
            'completed_at',
        ]
    
    def get_websocket_url(self, obj):
        request = self.context.get('request')
        if request and obj.status in ('pending', 'recording'):
            host = request.get_host()
            protocol = 'wss' if request.is_secure() else 'ws'
            return f"{protocol}://{host}/ws/video-stream/{obj.id}/"
        return None

    def get_challenge(self, obj):
        if obj.challenge_type == 'none' or not obj.challenge_data:
            return None
        data = obj.challenge_data
        return {
            'type': obj.challenge_type,
            'instructions': data.get('instructions', []),
            'text': data.get('text'),
            'nonce': data.get('nonce'),
        }
    
    def get_analysis(self, obj):
        if hasattr(obj, 'analysis_result') and obj.analysis_result:
            from apps.analysis.serializers import AnalysisResultSerializer
            return AnalysisResultSerializer(obj.analysis_result).data
        return None


class KYCSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    verdict = serializers.SerializerMethodField()
    overall_score = serializers.SerializerMethodField()
    
    class Meta:
        model = KYCSession
        fields = [
            'id',
            'external_reference',
            'applicant_name',
            'status',
            'verdict',
            'overall_score',
            'created_at',
            'completed_at',
        ]
    
    def get_verdict(self, obj):
        if hasattr(obj, 'analysis_result') and obj.analysis_result:
            return obj.analysis_result.verdict
        return None
    
    def get_overall_score(self, obj):
        if hasattr(obj, 'analysis_result') and obj.analysis_result:
            return float(obj.analysis_result.overall_score)
        return None
