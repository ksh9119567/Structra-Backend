import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler to provide consistent error responses.
    Ensures all authentication errors return the same format.
    Only handles AuthenticationFailed exceptions, lets other exceptions propagate.
    """
    # Call the default exception handler first
    response = exception_handler(exc, context)
    
    # Only customize AuthenticationFailed exceptions
    if isinstance(exc, AuthenticationFailed):
        response.data = {
            "detail": "User session has been invalidated. Please login again."
        }
        return response
    
    # For all other exceptions, return the default response
    return response
