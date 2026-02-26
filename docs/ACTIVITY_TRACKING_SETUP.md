# Activity Tracking Setup Guide

Quick guide to set up the activity tracking system in your Django project.

## Installation Steps

### 1. Apply Database Migrations

The ActivityLog model needs to be added to your database:

```bash
# Create migrations
python manage.py makemigrations core

# Apply migrations
python manage.py migrate core
```

### 2. Verify Middleware Configuration

The middleware should already be configured in `config/settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware
    'core.middleware.ActivityTrackingMiddleware',  # Should be last or near last
]
```

### 3. Verify App Installation

Ensure 'core' is in INSTALLED_APPS in `config/settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'core',  # Core app with activity tracking
    # ... other apps
]
```

### 4. Test the Setup

Start your development server:

```bash
python manage.py runserver
```

Make a test API request (e.g., login, create an organization) and then check:

```bash
# Check activity logs in Django shell
python manage.py shell

>>> from core.models import ActivityLog
>>> ActivityLog.objects.all()
>>> ActivityLog.objects.latest('timestamp')
```

Or via API:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/activity-logs/
```

### 5. Access Admin Panel

Visit the Django admin to view activity logs:
```
http://localhost:8000/admin/core/activitylog/
```

## Quick Test

### Test Activity Tracking

1. **Login** to get a token:
```bash
curl -X POST http://localhost:8000/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

2. **Create an organization** (or any resource):
```bash
curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Org"}'
```

3. **View your activities**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/activity-logs/my_activities/
```

You should see both the login and create organization activities logged!

## Configuration Options

### Exclude Specific Paths

Edit `core/middleware/activity_tracking.py`:

```python
EXCLUDED_PATHS = [
    '/static/',
    '/media/',
    '/health/',  # Add health check endpoint
    '/metrics/',  # Add metrics endpoint
]
```

### Track Only Specific Methods

```python
TRACKED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Remove 'GET' if too verbose
```

### Add Custom Sensitive Fields

```python
SENSITIVE_FIELDS = [
    'password',
    'token',
    'credit_card_number',  # Add your fields
    'social_security_number',
]
```

## Logging Configuration

Add activity logging to your logging configuration in `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/activity.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core.middleware.activity_tracking': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## Maintenance Setup

### Set Up Automated Cleanup

**Option 1: Cron Job**

Add to your crontab:
```bash
# Clean up logs older than 90 days, daily at 2 AM
0 2 * * * cd /path/to/project && /path/to/venv/bin/python manage.py cleanup_activity_logs --days=90
```

**Option 2: Celery Periodic Task**

Create a Celery task in `core/tasks.py`:

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def cleanup_old_activity_logs():
    call_command('cleanup_activity_logs', days=90)
```

Add to Celery beat schedule in `config/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-activity-logs-daily': {
        'task': 'core.tasks.cleanup_old_activity_logs',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

## Verification Checklist

- [ ] Migrations applied successfully
- [ ] Middleware is in MIDDLEWARE list
- [ ] 'core' app is in INSTALLED_APPS
- [ ] Can access `/api/v1/activity-logs/` endpoint
- [ ] Activity logs appear in Django admin
- [ ] Test activities are being logged
- [ ] Sensitive fields are redacted
- [ ] Cleanup command works

## Troubleshooting

### No logs are being created

1. Check middleware is enabled and in correct position
2. Run migrations: `python manage.py migrate core`
3. Check for errors in console/logs
4. Verify path is not in EXCLUDED_PATHS

### Permission denied errors

1. Ensure user is authenticated
2. Check API endpoint permissions
3. Verify JWT token is valid

### Database errors

1. Run migrations: `python manage.py migrate`
2. Check database connection
3. Verify core app is installed

### Performance issues

1. Add database indexes (should be automatic)
2. Implement log cleanup
3. Consider excluding GET requests
4. Use pagination when querying

## Next Steps

1. Review the full documentation: `docs/ACTIVITY_TRACKING.md`
2. Set up automated cleanup
3. Configure logging to files
4. Set up monitoring/alerting
5. Implement retention policies
6. Consider archiving strategies

## Support

For issues or questions:
1. Check the full documentation
2. Review Django logs for errors
3. Test with `--dry-run` flag for cleanup
4. Use Django shell to inspect ActivityLog model
