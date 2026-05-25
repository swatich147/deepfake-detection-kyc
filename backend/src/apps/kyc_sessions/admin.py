from django.contrib import admin

from .models import KYCSession, VideoChunk


class VideoChunkInline(admin.TabularInline):
    model = VideoChunk
    extra = 0
    readonly_fields = ('chunk_index', 's3_key', 'size_bytes', 'created_at')


@admin.register(KYCSession)
class KYCSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant_name', 'status', 'organization', 'created_at', 'completed_at')
    list_filter = ('status', 'challenge_type', 'organization')
    search_fields = ('id', 'external_reference', 'applicant_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    inlines = [VideoChunkInline]


@admin.register(VideoChunk)
class VideoChunkAdmin(admin.ModelAdmin):
    list_display = ('session', 'chunk_index', 'size_bytes', 'created_at')
    list_filter = ('session__status',)
