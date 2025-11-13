import uuid
import random
import string
from django.conf import settings
from datetime import timedelta

REDIS_PREFIX = "otp:"  # full keys will be like "otp:email:abc@x.com"
RESET_TOKEN_PREFIX = "password_reset_token:"
RESET_TOKEN_TTL = 15 * 60  # 15 minutes


def _make_key(kind: str, identifier: str) -> str:
    # kind: 'email', 'phone', 'login'
    return f"{REDIS_PREFIX}{kind}:{identifier}"

def generate_otp(length=6) -> str:
    # numeric OTP
    return ''.join(random.choices(string.digits, k=length))

def store_otp(kind: str, identifier: str, otp: str, ttl_seconds: int = 300):
    key = _make_key(kind, identifier)
    # store otp value — you can optionally store JSON with attempts/user_id
    settings.REDIS_CLIENT.setex(key, ttl_seconds, otp)

def get_otp(kind: str, identifier: str):
    key = _make_key(kind, identifier)
    val = settings.REDIS_CLIENT.get(key)
    # Redis client usually returns bytes; normalize to str
    if val is None:
        return None
    try:
        return val.decode("utf-8")
    except Exception:
        return str(val)

def verify_otp(kind: str, identifier: str, otp: str):
    key = _make_key(kind, identifier)
    stored = settings.REDIS_CLIENT.get(key)
    if not stored:
        return False
    # Normalize stored value to string for comparison
    try:
        stored_val = stored.decode("utf-8")
    except Exception:
        stored_val = str(stored)
    if stored_val == str(otp):
        settings.REDIS_CLIENT.delete(key)
        return True
    return False

def increment_attempts(kind: str, identifier: str, window_seconds: int = 60):
    key = f"{_make_key(kind, identifier)}:attempts"
    attempts = settings.REDIS_CLIENT.incr(key)
    if attempts == 1:
        settings.REDIS_CLIENT.expire(key, window_seconds)
    return attempts

def reset_attempts(kind: str, identifier: str):
    key = f"{_make_key(kind, identifier)}:attempts"
    settings.REDIS_CLIENT.delete(key)

def create_reset_token(user_id, ttl_seconds: int = RESET_TOKEN_TTL) -> str:
    token = uuid.uuid4().hex
    key = f"{RESET_TOKEN_PREFIX}{token}"
    # store user_id as string
    settings.REDIS_CLIENT.setex(key, ttl_seconds, str(user_id))
    return token

def get_userid_for_reset_token(token: str):
    key = f"{RESET_TOKEN_PREFIX}{token}"
    val = settings.REDIS_CLIENT.get(key)
    if not val:
        return None
    try:
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        # Return as string to handle both int and UUID string types
        return val
    except Exception:
        # stored value was not in expected format
        return None

def delete_reset_token(token: str):
    key = f"{RESET_TOKEN_PREFIX}{token}"
    settings.REDIS_CLIENT.delete(key)
