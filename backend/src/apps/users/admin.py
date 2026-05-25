from django.contrib import admin

from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('api_key', 'created_at', 'updated_at')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'organization', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'organization')
    search_fields = ('email', 'first_name', 'last_name')
