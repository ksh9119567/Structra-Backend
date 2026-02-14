import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from core.models import ActivityLog

logger = logging.getLogger(__name__)


class ActivityTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track user activities across the application.
    Logs all API requests with user info, request/response details, and timing.
    """
    
    # Paths to exclude from tracking
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
    ]
    
    # Methods to track (you can customize this)
    TRACKED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE', 'GET']
    
    # Sensitive fields to exclude from request body logging
    SENSITIVE_FIELDS = [
        'password',
        'token',
        'secret',
        'api_key',
        'access_token',
        'refresh_token',
        'otp',
        'credit_card',
        'ssn',
    ]
    
    def process_request(self, request):
        """Mark the start time of the request"""
        request._start_time = time.time()
        request._should_track = self._should_track_request(request)
        
    def process_response(self, request, response):
        """Log the activity after response is ready"""
        # Skip if tracking is disabled or path is excluded
        if not getattr(request, '_should_track', False):
            return response
        
        try:
            self._log_activity(request, response)
        except Exception as e:
            # Don't let logging errors break the application
            logger.error(f"Error logging activity: {str(e)}", exc_info=True)
        
        return response
    
    def _should_track_request(self, request):
        """Determine if this request should be tracked"""
        # Check if path is excluded
        for excluded_path in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded_path):
                return False
        
        # Check if method should be tracked
        if request.method not in self.TRACKED_METHODS:
            return False
        
        return True
    
    def _log_activity(self, request, response):
        """Create activity log entry"""
        # Calculate response time
        response_time = None
        if hasattr(request, '_start_time'):
            response_time = (time.time() - request._start_time) * 1000
        
        # Extract user info
        user = None
        username = 'Anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            username = user.email or user.username
        
        # Determine action type
        action = self._determine_action(request, response)
        
        # Extract resource info
        resource_type, resource_id, resource_name = self._extract_resource_info(request, response)
        
        # Get request body (sanitized)
        request_body = self._get_sanitized_request_body(request)
        
        # Get query params
        query_params = dict(request.GET) if request.GET else None
        
        # Create activity log
        ActivityLog.objects.create(
            user=user,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=self._generate_description(action, resource_type, resource_name, request),
            method=request.method,
            path=request.path,
            query_params=query_params,
            request_body=request_body,
            status_code=response.status_code,
            response_time_ms=round(response_time, 2) if response_time else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            extra_data=self._get_extra_data(request, response)
        )
        
        # Also log to file for real-time monitoring
        logger.info(
            f"Activity: {username} | {action} | {resource_type} | "
            f"{request.method} {request.path} | Status: {response.status_code} | "
            f"Time: {round(response_time, 2) if response_time else 'N/A'}ms"
        )
    
    def _determine_action(self, request, response):
        """Determine the action type based on method and path"""
        method = request.method
        path = request.path.lower()
        status_code = response.status_code
        
        # Failed requests
        if status_code >= 400:
            return 'FAILED'
        
        # Login/Logout
        if 'login' in path:
            return 'LOGIN'
        if 'logout' in path:
            return 'LOGOUT'
        
        # CRUD operations
        if method == 'POST':
            return 'CREATE'
        elif method == 'GET':
            return 'READ'
        elif method in ['PUT', 'PATCH']:
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        
        return 'ACCESS'
    
    def _extract_resource_info(self, request, response):
        """Extract resource type, ID, and name from request/response"""
        path = request.path
        resource_type = ''
        resource_id = ''
        resource_name = ''
        
        # Parse path to extract resource type
        path_parts = [p for p in path.split('/') if p]
        
        # Common patterns: /api/v1/organizations/, /api/v1/projects/uuid/
        if len(path_parts) >= 3:
            resource_type = path_parts[2].title().rstrip('s')  # e.g., 'organizations' -> 'Organization'
        
        # Try to get resource_id from query params or path
        if 'org_id' in request.GET:
            resource_id = request.GET.get('org_id')
        elif 'project_id' in request.GET:
            resource_id = request.GET.get('project_id')
        elif 'team_id' in request.GET:
            resource_id = request.GET.get('team_id')
        elif 'task_id' in request.GET:
            resource_id = request.GET.get('task_id')
        
        # Try to extract from request body
        if not resource_id and hasattr(request, 'data'):
            for key in ['org_id', 'project_id', 'team_id', 'task_id', 'id']:
                if key in request.data:
                    resource_id = str(request.data[key])
                    break
        
        # Try to get resource name from response
        if hasattr(response, 'data') and isinstance(response.data, dict):
            data = response.data.get('data', {})
            if isinstance(data, dict):
                resource_name = data.get('name', '') or data.get('title', '')
        
        return resource_type, resource_id, resource_name
    
    def _get_sanitized_request_body(self, request):
        """Get request body with sensitive fields removed"""
        if not hasattr(request, 'data') or not request.data:
            return None
        
        try:
            # Make a copy to avoid modifying original
            body = dict(request.data)
            
            # Remove sensitive fields
            for field in self.SENSITIVE_FIELDS:
                for key in list(body.keys()):
                    if field.lower() in key.lower():
                        body[key] = '***REDACTED***'
            
            return body
        except Exception as e:
            logger.debug(f"Could not sanitize request body: {str(e)}")
            return None
    
    def _generate_description(self, action, resource_type, resource_name, request):
        """Generate human-readable description of the activity"""
        if resource_name:
            return f"{action} {resource_type}: {resource_name}"
        elif resource_type:
            return f"{action} {resource_type}"
        else:
            return f"{action} {request.path}"
    
    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_extra_data(self, request, response):
        """Get additional context-specific data"""
        extra = {}
        
        # Add referer if available
        if request.META.get('HTTP_REFERER'):
            extra['referer'] = request.META.get('HTTP_REFERER')
        
        # Add content type
        if request.content_type:
            extra['content_type'] = request.content_type
        
        # Add response content type
        if hasattr(response, 'content_type'):
            extra['response_content_type'] = response.content_type
        
        return extra if extra else None
