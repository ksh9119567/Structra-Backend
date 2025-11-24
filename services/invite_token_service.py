import uuid
import random
import string
from django.conf import settings
from datetime import timedelta

REDIS_PREFIX = "invite:"  # full keys will be like "invite:email:abc@x.com"
INVITE_TOKEN_PREFIX = "invite_token:"
INVITE_TOKEN_TTL = 24 * 60 * 60  # 1 day


def store_invite_token(user_id, invite_type, ttl_seconds: int = INVITE_TOKEN_TTL) -> str:
    token = uuid.uuid4().hex
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    # store user_id as string
    settings.REDIS_CLIENT.setex(key, ttl_seconds, str(user_id))
    return token

def verify_invite_token(invite_type, token: str):
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    val = settings.REDIS_CLIENT.get(key)
    if not val:
        return None
    try:
        user_id = val
        return user_id
    except Exception:
        # stored value was not in expected format
        return None
    
def delete_invite_token(invite_type, token: str):
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    settings.REDIS_CLIENT.delete(key)