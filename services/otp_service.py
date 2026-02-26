import uuid
import random
import string
import logging

from datetime import timedelta

from django.conf import settings

logger = logging.getLogger(__name__)

REDIS_PREFIX = "otp:"  # full keys will be like "otp:email:abc@x.com"
RESET_TOKEN_PREFIX = "password_reset_token:"
RESET_TOKEN_TTL = 15 * 60  # 15 minutes


def _make_key(kind: str, identifier: str) -> str:
    # kind: 'email', 'phone', 'login'
    return f"{REDIS_PREFIX}{kind}:{identifier}"

def generate_otp(length=6) -> str:
    # numeric OTP
    otp = ''.join(random.choices(string.digits, k=length))
    logger.debug(f"Generated OTP of length {length}")
    return otp

def store_otp(kind: str, identifier: str, otp: str, ttl_seconds: int = 300):
    logger.debug(f"Storing OTP for {kind}: {identifier}, TTL: {ttl_seconds}s")
    key = _make_key(kind, identifier)
    # store otp value — you can optionally store JSON with attempts/user_id
    settings.REDIS_CLIENT.setex(key, ttl_seconds, otp)
    logger.info(f"OTP stored successfully for {kind}: {identifier}")

def get_otp(kind: str, identifier: str):
    logger.debug(f"Getting OTP for {kind}: {identifier}")
    key = _make_key(kind, identifier)
    val = settings.REDIS_CLIENT.get(key)
    # Redis client usually returns bytes; normalize to str
    if val is None:
        logger.warning(f"OTP not found for {kind}: {identifier}")
        return None
    try:
        return val.decode("utf-8")
    except Exception:
        return str(val)

def verify_otp(kind: str, identifier: str, otp: str):
    logger.debug(f"Verifying OTP for {kind}: {identifier}")
    key = _make_key(kind, identifier)
    stored = settings.REDIS_CLIENT.get(key)
    if not stored:
        logger.warning(f"OTP not found or expired for {kind}: {identifier}")
        return False
    # Normalize stored value to string for comparison
    try:
        stored_val = stored.decode("utf-8")
    except Exception:
        stored_val = str(stored)
    if stored_val == str(otp):
        settings.REDIS_CLIENT.delete(key)
        logger.info(f"OTP verified successfully for {kind}: {identifier}")
        return True
    logger.warning(f"OTP verification failed for {kind}: {identifier}")
    return False

def increment_attempts(kind: str, identifier: str, window_seconds: int = 60):
    logger.debug(f"Incrementing attempts for {kind}: {identifier}")
    key = f"{_make_key(kind, identifier)}:attempts"
    attempts = settings.REDIS_CLIENT.incr(key)
    if attempts == 1:
        settings.REDIS_CLIENT.expire(key, window_seconds)
    logger.debug(f"Attempts count for {kind}: {identifier} = {attempts}")
    return attempts

def reset_attempts(kind: str, identifier: str):
    logger.debug(f"Resetting attempts for {kind}: {identifier}")
    key = f"{_make_key(kind, identifier)}:attempts"
    settings.REDIS_CLIENT.delete(key)
    logger.info(f"Attempts reset for {kind}: {identifier}")

def create_reset_token(user_id, ttl_seconds: int = RESET_TOKEN_TTL) -> str:
    logger.debug(f"Creating password reset token for user {user_id}")
    token = uuid.uuid4().hex
    key = f"{RESET_TOKEN_PREFIX}{token}"
    # store user_id as string
    settings.REDIS_CLIENT.setex(key, ttl_seconds, str(user_id))
    logger.info(f"Password reset token created for user {user_id}")
    return token

def get_userid_for_reset_token(token: str):
    logger.debug("Getting user ID for reset token")
    key = f"{RESET_TOKEN_PREFIX}{token}"
    val = settings.REDIS_CLIENT.get(key)
    if not val:
        logger.warning("Reset token not found or expired")
        return None
    try:
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        # Return as string to handle both int and UUID string types
        logger.info("Reset token validated successfully")
        return val
    except Exception as e:
        # stored value was not in expected format
        logger.error(f"Error getting user ID for reset token: {str(e)}")
        return None

def delete_reset_token(token: str):
    logger.debug("Deleting reset token")
    key = f"{RESET_TOKEN_PREFIX}{token}"
    settings.REDIS_CLIENT.delete(key)
    logger.info("Reset token deleted")
