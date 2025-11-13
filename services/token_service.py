import redis

from datetime import timedelta
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

REDIS_KEY_PREFIX = "refresh:"

def store_refresh_token(user_id, refresh_token):
    """Store refresh token in Redis with expiry."""
    # prefer configured lifetime if available
    try:
        ttl = int(settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME", timedelta(days=7)).total_seconds())
    except Exception:
        ttl = int(timedelta(days=7).total_seconds())
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    settings.REDIS_CLIENT.setex(key, ttl, str(user_id))


def is_refresh_token_valid(refresh_token):
    """Check if refresh token exists in Redis."""
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    # redis-py returns int count for exists in older clients, newer return bool
    val = settings.REDIS_CLIENT.exists(key)
    return bool(val)


def delete_refresh_token(refresh_token):
    """Invalidate refresh token on logout."""
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    settings.REDIS_CLIENT.delete(key)
