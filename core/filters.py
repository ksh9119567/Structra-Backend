import django_filters
from core.models import ActivityLog


class ActivityLogFilter(django_filters.FilterSet):
    """Filter for ActivityLog queryset"""
    
    action = django_filters.ChoiceFilter(choices=ActivityLog.ACTION_CHOICES)
    resource_type = django_filters.CharFilter(lookup_expr='iexact')
    method = django_filters.CharFilter()
    status_code = django_filters.NumberFilter()
    status_code_gte = django_filters.NumberFilter(field_name='status_code', lookup_expr='gte')
    status_code_lte = django_filters.NumberFilter(field_name='status_code', lookup_expr='lte')
    
    # Date range filters
    timestamp_after = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    # User filter (for admin)
    username = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = ActivityLog
        fields = [
            'action',
            'resource_type',
            'method',
            'status_code',
            'username',
        ]
