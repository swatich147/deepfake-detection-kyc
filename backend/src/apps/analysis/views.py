"""Analysis views."""
from django.db import models
from django.db.models import Count, Avg
from django.db.models.functions import TruncDate
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnalysisResult, FrameScore
from .serializers import AnalysisResultSerializer, FrameScoreSerializer


class AnalysisDetailView(generics.RetrieveAPIView):
    """Get analysis result for a session."""
    serializer_class = AnalysisResultSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'session_id'
    
    def get_queryset(self):
        return AnalysisResult.objects.filter(
            session__organization=self.request.user.organization
        )


class FrameScoresView(generics.ListAPIView):
    """Get frame-level scores for an analysis."""
    serializer_class = FrameScoreSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        session_id = self.kwargs['session_id']
        return FrameScore.objects.filter(
            result__session_id=session_id,
            result__session__organization=self.request.user.organization
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filter by frame range
        from_frame = request.query_params.get('from_frame')
        to_frame = request.query_params.get('to_frame')
        anomalies_only = request.query_params.get('anomalies_only') == 'true'
        
        if from_frame:
            queryset = queryset.filter(frame_number__gte=int(from_frame))
        if to_frame:
            queryset = queryset.filter(frame_number__lte=int(to_frame))
        if anomalies_only:
            queryset = queryset.filter(is_anomaly=True)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'session_id': self.kwargs['session_id'],
            'total_frames': queryset.count(),
            'frames': serializer.data
        })


class AnalysisStatsView(generics.GenericAPIView):
    """Get aggregate analysis statistics."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        # Get date range from query params
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if not from_date:
            from_date = (timezone.now() - timedelta(days=30)).date()
        if not to_date:
            to_date = timezone.now().date()
        
        # Filter by organization and date
        results = AnalysisResult.objects.filter(
            session__organization=request.user.organization,
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )
        
        # Aggregate stats
        total = results.count()
        by_verdict = results.values('verdict').annotate(count=Count('id'))
        avg_score = results.aggregate(avg=Avg('overall_score'))['avg']
        avg_processing = results.aggregate(avg=Avg('processing_time_ms'))['avg']
        
        # Daily trend
        daily = results.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            sessions=Count('id'),
            flagged=Count('id', filter=models.Q(verdict='fake') | models.Q(verdict='suspicious'))
        ).order_by('date')
        
        return Response({
            'period': {
                'from': str(from_date),
                'to': str(to_date),
            },
            'summary': {
                'total_sessions': total,
                'avg_score': float(avg_score) if avg_score else 0,
                'avg_processing_time_ms': int(avg_processing) if avg_processing else 0,
            },
            'verdict_breakdown': {
                item['verdict']: item['count'] for item in by_verdict
            },
            'daily_trend': list(daily),
        })
