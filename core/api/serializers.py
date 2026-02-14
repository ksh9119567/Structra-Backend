from rest_framework import serializers
from core.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for ActivityLog model"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'user',
            'user_email',
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
        read_only_fields = fields


class ActivityLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing activity logs"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'user_email',
            'username',
            'action',
            'resource_type',
            'resource_name',
            'description',
            'method',
            'path',
            'status_code',
            'response_time_ms',
            'timestamp',
        ]
        read_only_fields = fields
