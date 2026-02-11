from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied
from services.token_service import store_refresh_token, delete_refresh_token
from app.accounts.models import User


def login_user(user):
    refresh = RefreshToken.for_user(user)
    store_refresh_token(user.id, str(refresh))
    return refresh


def logout_user(*, refresh_token, request_user):
    try:
        token = RefreshToken(refresh_token)
        uid = token.get("user_id") or token.get("user")
        if uid and str(uid) != str(request_user.id):
            raise PermissionDenied("Token does not belong to user")
    except Exception:
        pass

    delete_refresh_token(refresh_token)
