from django.contrib import admin

from .models import AnalysisResult, FrameScore


class FrameScoreInline(admin.TabularInline):
    model = FrameScore
    extra = 0
    readonly_fields = ('frame_number', 'timestamp_ms', 'manipulation_score', 'is_anomaly')


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('session', 'verdict', 'overall_score', 'frames_analyzed', 'created_at')
    list_filter = ('verdict',)
    readonly_fields = ('id', 'created_at')
    inlines = [FrameScoreInline]
