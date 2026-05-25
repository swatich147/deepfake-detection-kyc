from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'request_method', 'request_path', 'response_status', 'created_at')
    list_filter = ('action', 'request_method', 'response_status')
    search_fields = ('request_path', 'user__email')
    readonly_fields = ('created_at',)
