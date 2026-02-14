import os
import logging

from celery import Celery

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings

logger.info("Initializing Celery application")
app = Celery("config")

# Use a string here so worker doesn't have to pickle the object when using Windows
app.config_from_object("django.conf:settings", namespace="CELERY")

# Broker: use Redis by default (read from settings or env)

app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND

# Optional useful settings:
app.conf.task_track_started = True
app.conf.task_time_limit = 30 * 60  # 30 minutes per task default

logger.info("Celery configuration completed, autodiscovering tasks")
app.autodiscover_tasks()
logger.info("Celery application ready")
