"""Analysis URL patterns."""
from django.urls import path
from .views import AnalysisDetailView, FrameScoresView, AnalysisStatsView

urlpatterns = [
    path('stats/', AnalysisStatsView.as_view(), name='analysis-stats'),
    path('<uuid:session_id>/', AnalysisDetailView.as_view(), name='analysis-detail'),
    path('<uuid:session_id>/frames/', FrameScoresView.as_view(), name='analysis-frames'),
]
