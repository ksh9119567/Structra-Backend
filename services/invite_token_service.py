import uuid
import random
import string
import logging

from datetime import timedelta

from django.conf import settings

logger = logging.getLogger(__name__)

REDIS_PREFIX = "invite:"  # full keys will be like "invite:email:abc@x.com"
INVITE_TOKEN_PREFIX = "invite_token:"
INVITE_TOKEN_TTL = 24 * 60 * 60  # 1 day


def store_invite_token(user_id, invite_type, ttl_seconds: int = INVITE_TOKEN_TTL) -> str:
    logger.debug(f"Storing invite token for user {user_id}, type: {invite_type}")
    token = uuid.uuid4().hex
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    # store user_id as string
    settings.REDIS_CLIENT.setex(key, ttl_seconds, str(user_id))
    logger.info(f"Invite token stored successfully for user {user_id}, type: {invite_type}")
    return token

def delete_invite_token(invite_type, token: str):
    logger.debug(f"Deleting invite token, type: {invite_type}")
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    settings.REDIS_CLIENT.delete(key)
    logger.info(f"Invite token deleted, type: {invite_type}")
    
def verify_invite_token(invite_type, token: str):
    logger.debug(f"Verifying invite token, type: {invite_type}")
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    val = settings.REDIS_CLIENT.get(key)
    if not val:
        logger.warning(f"Invite token not found or expired, type: {invite_type}")
        return None
    try:
        user_id = val
        delete_invite_token(invite_type, token)
        logger.info(f"Invite token verified successfully for user {user_id}, type: {invite_type}")
        return user_id
    except Exception as e:
        # stored value was not in expected format
        logger.error(f"Error verifying invite token, type: {invite_type}, error: {str(e)}")
        return None
    
