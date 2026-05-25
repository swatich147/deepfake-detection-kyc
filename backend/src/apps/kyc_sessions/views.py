"""KYC Session views."""
import random
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
import json

from .models import KYCSession
from .challenge import build_challenge_payload
from .throttling import SessionCreateThrottle, AnalysisExportThrottle
from .serializers import (
    KYCSessionSerializer,
    KYCSessionCreateSerializer,
    KYCSessionListSerializer,
)


class KYCSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for KYC sessions."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['external_reference', 'applicant_name']
    ordering_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    
    def get_throttles(self):
        if self.action == 'create':
            return [SessionCreateThrottle()]
        if self.action in ('export', 'export_all'):
            return [AnalysisExportThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        user = self.request.user
        return KYCSession.objects.filter(
            organization=user.organization
        ).select_related('created_by').prefetch_related('analysis_result')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KYCSessionCreateSerializer
        if self.action == 'list':
            return KYCSessionListSerializer
        return KYCSessionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create session and return full payload including WebSocket URL."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        session = serializer.instance
        output = KYCSessionSerializer(session, context={'request': request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """Create session with organization and challenge."""
        session = serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

        if session.challenge_type != 'none':
            session.challenge_data = self._generate_challenge(session.challenge_type)
            session.save(update_fields=['challenge_data', 'updated_at'])
    
    def _generate_challenge(self, challenge_type):
        """Generate challenge with nonce anti-replay (Phase 4)."""
        if challenge_type == 'random_movement':
            movements = ['Look left', 'Look right', 'Look up', 'Look down', 'Tilt head left', 'Tilt head right']
            payload = {
                'instructions': random.sample(movements, 3),
                'duration_per_instruction': 3,
            }
        elif challenge_type == 'blink':
            payload = {
                'instructions': ['Blink twice', 'Keep eyes open for 3 seconds'],
                'duration_per_instruction': 4,
            }
        elif challenge_type == 'read_text':
            texts = [
                'I confirm this is a live verification',
                "Today's date is important to me",
                'I am verifying my identity now',
            ]
            payload = {'text': random.choice(texts), 'duration': 10, 'instructions': ['Read the text aloud']}
        else:
            payload = {}
        return build_challenge_payload(challenge_type, payload)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export session + analysis as JSON (Phase 3 reporting)."""
        session = self.get_object()
        data = KYCSessionSerializer(session, context={'request': request}).data
        if hasattr(session, 'analysis_result') and session.analysis_result:
            from apps.analysis.serializers import AnalysisResultSerializer, FrameScoreSerializer
            result = session.analysis_result
            data['analysis_detail'] = AnalysisResultSerializer(result).data
            data['frames'] = FrameScoreSerializer(result.frame_scores.all(), many=True).data
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json',
        )
        response['Content-Disposition'] = f'attachment; filename="session-{session.id}.json"'
        return response

    @action(detail=False, methods=['get'], url_path='export')
    def export_all(self, request):
        """Export all organization sessions summary (Phase 3)."""
        sessions = self.get_queryset()[:500]
        rows = KYCSessionListSerializer(sessions, many=True).data
        response = HttpResponse(
            json.dumps({'sessions': rows, 'count': len(rows)}, indent=2, default=str),
            content_type='application/json',
        )
        response['Content-Disposition'] = 'attachment; filename="kyc-sessions-export.json"'
        return response
    
    @action(detail=True, methods=['post'])
    def complete_recording(self, request, pk=None):
        """Mark recording as complete and start processing."""
        session = self.get_object()
        
        if session.status not in ['pending', 'recording']:
            return Response(
                {'error': 'Session cannot be processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'processing'
        session.save()
        
        from .processing import schedule_processing
        schedule_processing(str(session.id))
        
        return Response({
            'status': 'processing',
            'message': 'Video processing started'
        })
    
    @action(detail=True, methods=['delete'])
    def delete_data(self, request, pk=None):
        """GDPR: Delete all session data."""
        session = self.get_object()
        
        from .services import LocalMediaService
        media = LocalMediaService()

        if session.video_s3_key:
            media.delete_path(session.video_s3_key)

        for chunk in session.chunks.all():
            media.delete_path(chunk.s3_key)

        media.delete_session_chunks(str(session.id))
        
        # Delete session (cascades to analysis results)
        session.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
