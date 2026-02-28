import logging

from rest_framework.exceptions import ValidationError

from app.accounts.models import User
from services.otp_service import (
    generate_otp, store_otp, verify_otp, increment_attempts, create_reset_token, 
    get_userid_for_reset_token, delete_reset_token,
)
from services.notification_services import send_email_otp_async, send_sms_otp

logger = logging.getLogger(__name__)


def request_password_reset(*, kind, identifier):
    logger.info(f"Password reset requested for {kind}: {identifier}")
    attempts = increment_attempts(f"password_request:{kind}", identifier=identifier, window_seconds=60)
    if attempts > 5:
        logger.warning(f"Too many password reset requests for {kind}: {identifier}")
        raise ValidationError("Too many OTP requests. Try again later.")
    try:
        user = (
            User.objects.get(email=identifier) if kind == "email"
            else User.objects.get(phone_no=identifier)
        )
        if kind == "email" and not user.is_email_verified:
            logger.warning(f"Email not verified for password reset: {identifier}")
            raise ValidationError("Email ID not verified. Please verify your email id first.")
        elif kind == "phone" and not user.is_phone_verified:
            logger.warning(f"Phone not verified for password reset: {identifier}")
            raise ValidationError("Phone number not verified. Please verify your phone number first.")
        
    except User.DoesNotExist:
        logger.warning(f"User not found for password reset: {kind}: {identifier}")
        raise ValidationError("User does not exist. Please register.")
    
    otp = generate_otp()
    store_otp(f"password:{kind}", identifier, otp)

    if kind == "email":
        send_email_otp_async(identifier, otp)
    else:
        send_sms_otp(identifier, otp)
    logger.info(f"Password reset OTP sent for {kind}: {identifier}")


def verify_password_reset_otp(*, kind, identifier, otp):
    logger.info(f"Verifying password reset OTP for {kind}: {identifier}")
    attempts = increment_attempts(f"password_verify:{kind}", identifier, 300)
    if attempts > 5:
        logger.warning(f"Too many password reset OTP verification attempts for {kind}: {identifier}")
        raise ValidationError("Too many attempts")

    if not verify_otp(f"password:{kind}", identifier, otp):
        logger.warning(f"Invalid password reset OTP for {kind}: {identifier}")
        raise ValidationError("Invalid OTP")

    user = (
        User.objects.get(email=identifier)
        if kind == "email"
        else User.objects.get(phone_no=identifier)
    )
    logger.info(f"Password reset OTP verified for user: {user.email}")
    return create_reset_token(user.id)


def reset_password(*, reset_token, new_password):
    logger.info("Resetting password with reset token")
    user_id = get_userid_for_reset_token(reset_token)
    if not user_id:
        logger.warning("Invalid or expired reset token")
        raise ValidationError("Invalid or expired reset token")

    user = User.objects.get(pk=user_id)
    user.set_password(new_password)
    user.save(update_fields=["password"])

    delete_reset_token(reset_token)
    logger.info(f"Password reset successfully for user: {user.email}")
