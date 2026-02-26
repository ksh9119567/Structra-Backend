import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from services.token_service import is_access_token_valid

logger = logging.getLogger(__name__)


class ValidatedJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates both the JWT signature
    and checks if the access token is still valid in Redis.
    This ensures logged-out users cannot use their existing access tokens.
    """
    
    def authenticate(self, request):
        try:
            # First, perform standard JWT authentication
            result = super().authenticate(request)
            
            if result is None:
                return None
            
            user, validated_token = result
            
            # Get the raw token from the Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                logger.warning(f"Invalid authorization header format for user {user.id}")
                raise AuthenticationFailed("User session has been invalidated. Please login again.")
            
            access_token = auth_header.split(' ')[1]
            
            # Check if the access token is still valid in Redis (user hasn't logged out)
            if not is_access_token_valid(access_token):
                logger.warning(f"Access token invalid or expired for user {user.id}")
                raise AuthenticationFailed("User session has been invalidated. Please login again.")
            
            return user, validated_token
        
        except AuthenticationFailed:
            # Re-raise our custom authentication failures
            raise
        except Exception as e:
            # Catch JWT validation errors and provide consistent response
            logger.warning(f"Authentication error: {str(e)}")
            raise AuthenticationFailed("User session has been invalidated. Please login again.")