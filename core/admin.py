from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp',
        'username',
        'action',
        'resource_type',
        'resource_name',
        'method',
        'status_code',
        'response_time_ms',
        'ip_address',
    ]
    list_filter = [
        'action',
        'resource_type',
        'method',
        'status_code',
        'timestamp',
    ]
    search_fields = [
        'username',
        'resource_type',
        'resource_name',
        'path',
        'ip_address',
        'description',
    ]
    readonly_fields = [
        'id',
        'user',
        'username',
        'action',
        'resource_type',
        'resource_id',
        'resource_name',
        'description',
        'method',
        'path',
        'query_params',
        'request_body',
        'status_code',
        'response_time_ms',
        'ip_address',
        'user_agent',
        'timestamp',
        'extra_data',
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        # Activity logs should only be created by the system
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete activity logs
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        # Activity logs should not be editable
        return False
