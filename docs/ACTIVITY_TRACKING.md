# Activity Tracking System

This document describes the comprehensive activity tracking system implemented in the project.

## Overview

The activity tracking system automatically logs all user activities across the application, providing:
- Complete audit trail of user actions
- Security monitoring and anomaly detection
- Performance metrics and analytics
- Compliance with regulatory requirements (GDPR, HIPAA, SOX, PCI DSS, ISO 27001)

## Implementation Summary

### Files Created

**Core Models & Middleware:**
- `core/models.py` - ActivityLog model with all tracking fields
- `core/middleware/activity_tracking.py` - Middleware that intercepts and logs requests
- `core/admin.py` - Django admin interface for viewing logs

**API Layer:**
- `core/api/serializers.py` - Serializers for ActivityLog
- `core/api/views.py` - ViewSet with endpoints to query activity logs
- `core/api/filters.py` - Filters for searching/filtering logs
- `core/api/urls.py` - URL routing for activity log API

**Management Commands:**
- `core/management/commands/cleanup_activity_logs.py` - Command to clean old logs

**Configuration Updates:**
- `config/settings.py` - Added middleware and 'core' app
- `config/urls.py` - Added activity logs API endpoints

## Features

### Automatic Tracking
- **All API Requests**: Tracks POST, PUT, PATCH, DELETE, and GET requests
- **User Actions**: Records who did what, when, and from where
- **Resource Changes**: Logs changes to organizations, projects, teams, and tasks
- **Authentication Events**: Tracks login, logout, and failed authentication attempts
- **Performance Metrics**: Records response times for each request

### Data Captured
- User information (email, ID)
- Action type (CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
- Resource details (type, ID, name)
- Request details (method, path, query params, body)
- Response details (status code, response time)
- Client information (IP address, user agent)
- Timestamp and additional metadata

### Security Features
- **Sensitive Data Redaction**: Automatically removes passwords, tokens, and other sensitive fields
- **IP Tracking**: Records client IP addresses for security analysis
- **Failed Request Logging**: Tracks all failed requests (4xx, 5xx errors)
- **Immutable Logs**: Activity logs cannot be edited or deleted by regular users

## Usage

### Viewing Activity Logs

#### API Endpoints

**List your own activities:**
```bash
GET /api/v1/activity-logs/
```

**Get specific activity log:**
```bash
GET /api/v1/activity-logs/{id}/
```

**Get your recent activities:**
```bash
GET /api/v1/activity-logs/my_activities/
```

**Get activity statistics:**
```bash
GET /api/v1/activity-logs/stats/
```

#### Filtering

You can filter activity logs using query parameters:

```bash
# Filter by action type
GET /api/v1/activity-logs/?action=CREATE

# Filter by resource type
GET /api/v1/activity-logs/?resource_type=Project

# Filter by HTTP method
GET /api/v1/activity-logs/?method=POST

# Filter by status code
GET /api/v1/activity-logs/?status_code=200
GET /api/v1/activity-logs/?status_code_gte=400

# Filter by date range
GET /api/v1/activity-logs/?timestamp_after=2024-01-01T00:00:00Z
GET /api/v1/activity-logs/?timestamp_before=2024-12-31T23:59:59Z

# Search
GET /api/v1/activity-logs/?search=organization

# Ordering
GET /api/v1/activity-logs/?ordering=-timestamp
GET /api/v1/activity-logs/?ordering=response_time_ms
```

#### Admin Access

Admin users can view all activity logs in the Django admin panel:
```
/admin/core/activitylog/
```

### Example Response

```json
{
  "id": "uuid-here",
  "user_email": "user@example.com",
  "username": "user@example.com",
  "action": "CREATE",
  "resource_type": "Project",
  "resource_id": "project-uuid",
  "resource_name": "My New Project",
  "description": "CREATE Project: My New Project",
  "method": "POST",
  "path": "/api/v1/projects/",
  "query_params": null,
  "request_body": {
    "name": "My New Project",
    "description": "Project description"
  },
  "status_code": 201,
  "response_time_ms": 145.23,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:00Z",
  "extra_data": {
    "content_type": "application/json"
  }
}
```

## Configuration

### Customizing Tracked Paths

Edit `core/middleware/activity_tracking.py`:

```python
# Paths to exclude from tracking
EXCLUDED_PATHS = [
    '/static/',
    '/media/',
    '/admin/jsi18n/',
    '/favicon.ico',
    '/your-custom-path/',  # Add your paths here
]
```

### Customizing Tracked Methods

```python
# Methods to track
TRACKED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE', 'GET']
```

### Adding Sensitive Fields

```python
# Sensitive fields to exclude from request body logging
SENSITIVE_FIELDS = [
    'password',
    'token',
    'secret',
    'api_key',
    'your_sensitive_field',  # Add your fields here
]
```

## Maintenance

### Cleaning Up Old Logs

To prevent database bloat, regularly clean up old activity logs:

```bash
# Dry run - see what would be deleted
python manage.py cleanup_activity_logs --days=90 --dry-run

# Actually delete logs older than 90 days
python manage.py cleanup_activity_logs --days=90

# Delete logs older than 30 days
python manage.py cleanup_activity_logs --days=30
```

### Automated Cleanup

Add to your cron jobs or task scheduler:

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python manage.py cleanup_activity_logs --days=90
```

Or use Celery periodic tasks:

```python
# In your celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-activity-logs': {
        'task': 'core.tasks.cleanup_old_activity_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

## Performance Considerations

### Database Indexes

The ActivityLog model includes indexes on frequently queried fields:
- `timestamp` + `user`
- `resource_type` + `resource_id`
- `action` + `status_code`

### Query Optimization

When querying activity logs:
- Use `select_related('user')` to avoid N+1 queries
- Apply filters before pagination
- Use date range filters to limit result sets
- Consider archiving very old logs to separate storage

### Storage Management

Activity logs can grow quickly. Consider:
- Regular cleanup of old logs (90-180 days retention)
- Archiving important logs to cold storage
- Using database partitioning for large datasets
- Implementing log rotation strategies

## Security Best Practices

1. **Access Control**: Only authenticated users can view their own logs; admins can view all
2. **Data Redaction**: Sensitive fields are automatically redacted
3. **Immutability**: Logs cannot be edited after creation
4. **Audit Trail**: All access to activity logs is itself logged
5. **Retention Policy**: Implement appropriate retention policies for your compliance needs

## Compliance

This activity tracking system helps meet compliance requirements for:

- **GDPR**: Right to access, data portability, audit trails
- **HIPAA**: Access logs, audit trails, security monitoring
- **SOX**: Financial data access tracking
- **PCI DSS**: Access control monitoring
- **ISO 27001**: Information security management

## Troubleshooting

### Logs Not Being Created

1. Check middleware is enabled in `settings.py`
2. Verify database migrations are applied: `python manage.py migrate`
3. Check logs for errors: Look for activity tracking errors in application logs
4. Verify user is authenticated for user-specific tracking

### Performance Issues

1. Check database indexes are created
2. Implement log cleanup for old entries
3. Consider excluding high-frequency endpoints
4. Use pagination when querying logs

### Missing Data

1. Verify the path is not in `EXCLUDED_PATHS`
2. Check the HTTP method is in `TRACKED_METHODS`
3. Ensure middleware is properly configured
4. Check for exceptions in middleware execution

## API Examples

### Python/Requests

```python
import requests

# Get your activity logs
response = requests.get(
    'http://localhost:8000/api/v1/activity-logs/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
activities = response.json()

# Filter by action
response = requests.get(
    'http://localhost:8000/api/v1/activity-logs/',
    params={'action': 'CREATE'},
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

# Get statistics
response = requests.get(
    'http://localhost:8000/api/v1/activity-logs/stats/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
stats = response.json()
```

### JavaScript/Fetch

```javascript
// Get activity logs
fetch('/api/v1/activity-logs/', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(response => response.json())
.then(data => console.log(data));

// Get recent activities
fetch('/api/v1/activity-logs/my_activities/', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

## What Gets Logged

For each request, the system logs:

```json
{
  "user": "user@example.com",
  "action": "CREATE",
  "resource_type": "Project",
  "resource_id": "uuid-123",
  "resource_name": "My Project",
  "description": "CREATE Project: My Project",
  "method": "POST",
  "path": "/api/v1/projects/",
  "query_params": {},
  "request_body": {"name": "My Project"},
  "status_code": 201,
  "response_time_ms": 145.23,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Benefits

1. **Compliance**: Meets GDPR, HIPAA, SOX, PCI DSS, ISO 27001 requirements
2. **Security**: Detect suspicious activities and unauthorized access attempts
3. **Debugging**: Trace issues by seeing exact sequence of user actions
4. **Analytics**: Understand user behavior and feature usage patterns
5. **Audit Trail**: Complete history of who did what and when
6. **Performance**: Track slow endpoints and response times

## Future Enhancements

Potential improvements to consider:
- Real-time activity streaming via WebSockets
- Advanced analytics dashboard
- Anomaly detection and alerting
- Export to external logging systems (ELK, Splunk)
- Machine learning for behavior analysis
- Geolocation tracking
- Session tracking and correlation
