import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from core.models import ActivityLog
from core.api.serializers import ActivityLogSerializer, ActivityLogListSerializer
from core.api.filters import ActivityLogFilter
from core.pagination import StandardPagination

logger = logging.getLogger(__name__)


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing activity logs.
    Only authenticated users can view their own activities.
    Admin users can view all activities.
    """
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    pagination_class = StandardPagination
    filterset_class = ActivityLogFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'resource_type', 'resource_name', 'description', 'path']
    ordering_fields = ['timestamp', 'response_time_ms', 'status_code']
    ordering = ['-timestamp']
    
    def get_permissions(self):
        """
        Regular users can view their own activities.
        Admin users can view all activities.
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users see only their own activities.
        Admin users see all activities.
        """
        logger.info(f"Fetching activity logs for user: {self.request.user.email}")
        
        queryset = ActivityLog.objects.select_related('user').all()
        
        # Non-admin users can only see their own activities
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            logger.debug(f"Filtered to user's own activities: {self.request.user.email}")
        
        return queryset
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return ActivityLogListSerializer
        return ActivityLogSerializer
    
    def list(self, request, *args, **kwargs):
        """List activity logs with pagination"""
        logger.info(f"Listing activity logs for user: {request.user.email}")
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.debug(f"Returning {len(page)} activity logs")
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single activity log"""
        logger.info(f"Retrieving activity log: {kwargs.get('pk')} by user: {request.user.email}")
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_activities(self, request):
        """Get current user's recent activities"""
        logger.info(f"Fetching recent activities for user: {request.user.email}")
        
        activities = ActivityLog.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:50]
        
        serializer = ActivityLogListSerializer(activities, many=True)
        logger.debug(f"Returning {len(activities)} recent activities")
        
        return Response({
            'message': 'Success',
            'count': len(activities),
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get activity statistics"""
        logger.info(f"Fetching activity stats for user: {request.user.email}")
        
        queryset = self.get_queryset()
        
        stats = {
            'total_activities': queryset.count(),
            'by_action': {},
            'by_resource': {},
            'by_status': {},
        }
        
        # Count by action
        for action_choice in ActivityLog.ACTION_CHOICES:
            action_code = action_choice[0]
            count = queryset.filter(action=action_code).count()
            if count > 0:
                stats['by_action'][action_code] = count
        
        # Count by resource type
        resource_types = queryset.values_list('resource_type', flat=True).distinct()
        for resource_type in resource_types:
            if resource_type:
                count = queryset.filter(resource_type=resource_type).count()
                stats['by_resource'][resource_type] = count
        
        # Count by status code range
        stats['by_status'] = {
            'success_2xx': queryset.filter(status_code__gte=200, status_code__lt=300).count(),
            'redirect_3xx': queryset.filter(status_code__gte=300, status_code__lt=400).count(),
            'client_error_4xx': queryset.filter(status_code__gte=400, status_code__lt=500).count(),
            'server_error_5xx': queryset.filter(status_code__gte=500).count(),
        }
        
        logger.debug(f"Activity stats calculated: {stats['total_activities']} total")
        
        return Response({
            'message': 'Success',
            'data': stats
        })
