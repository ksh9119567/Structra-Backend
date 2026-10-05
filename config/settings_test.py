"""
Settings used by the automated test-suite (`python manage.py test` selects
them automatically - see manage.py).

Everything external is replaced so the tests are fast, isolated and need no
running services:

* database  - in-memory SQLite by default. Set TEST_DB=postgres to run the same
              suite against the PostgreSQL configured in .env (Django creates
              and drops a separate `test_<name>` database, never touching real
              data).
* Redis     - an in-memory FakeRedis (core/testing/fake_redis.py), so OTPs,
              token registry and rate limits work without a Redis server and the
              real Redis DB is never read or flushed.
* Celery    - tasks run eagerly in-process.
* e-mail    - captured in django.core.mail.outbox.
"""
import os

from config.settings import *  # noqa: F401,F403

from core.testing.fake_redis import FakeRedis

if os.getenv("TEST_DB", "sqlite").lower() != "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

REDIS_CLIENT = FakeRedis()

# Fast hashing - the suite creates many users.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "tests@structra.local"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Keep test output readable (the app logs every request at INFO).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
