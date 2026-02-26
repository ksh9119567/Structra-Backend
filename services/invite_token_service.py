import uuid
import logging
import json

from datetime import timedelta

from django.conf import settings

from rest_framework.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)

REDIS_PREFIX = "invite:"  # full keys will be like "invite:email:abc@x.com"
INVITE_TOKEN_PREFIX = "invite_token:"
INVITE_TOKEN_TTL = 24 * 60 * 60  # 1 day


def store_invite_token(user_id, invite_type, invited_by, entity, role, ttl_seconds: int = INVITE_TOKEN_TTL) -> str:
    logger.debug(f"Storing invite token for user {user_id}, type: {invite_type}")
    token = uuid.uuid4().hex
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    
    # Convert UUID and objects to strings for JSON serialization
    payload = {
        "user_id": str(user_id),
        "entity": str(entity),
        "entity_id": str(entity.id),
        "role": role,
        "invite_type": invite_type,
        "invited_by": str(invited_by) if invited_by else None
    }
    
    json_payload = json.dumps(payload)
    settings.REDIS_CLIENT.setex(key, ttl_seconds, json_payload)
    logger.info(f"Invite token stored successfully for user {user_id}, type: {invite_type}")
    return token

def delete_invite_token(invite_type, token: str):
    logger.debug(f"Deleting invite token, type: {invite_type}")
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    settings.REDIS_CLIENT.delete(key)
    logger.info(f"Invite token deleted, type: {invite_type}")
    
def verify_invite_token(request_user, invite_type, token: str):
    logger.debug(f"Verifying invite token, type: {invite_type}")
    key = f"{INVITE_TOKEN_PREFIX}{invite_type}:{token}"
    json_val = settings.REDIS_CLIENT.get(key)
    if not json_val:
        logger.warning(f"Invite token not found or expired, type: {invite_type}")
        raise ValidationError("Invite token not found or expired")
    try:
        val = json.loads(json_val)
        if str(request_user.id) != val["user_id"]:
            logger.warning(f"Token mismatch during invite token validation, type: {invite_type}")
            raise PermissionDenied("Token does not belong to user")
        delete_invite_token(invite_type, token)
        logger.info(f"Invite token verified successfully for user {val['user_id']}, type: {invite_type}")
        return val
    except Exception as e:
        # stored value was not in expected format
        logger.error(f"Error verifying invite token, type: {invite_type}, error: {str(e)}")
        return None
    
