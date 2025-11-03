import redis

from datetime import timedelta
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

REDIS_KEY_PREFIX = "refresh:"

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

def store_refresh_token(user_id, refresh_token):
    """Store refresh token in Redis with expiry."""
    ttl = int(timedelta(days=7).total_seconds())  # match SIMPLE_JWT lifetime
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    redis_client.setex(key, ttl, user_id)


def is_refresh_token_valid(refresh_token):
    """Check if refresh token exists in Redis."""
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    return redis_client.exists(key)


def delete_refresh_token(refresh_token):
    """Invalidate refresh token on logout."""
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    redis_client.delete(key)
