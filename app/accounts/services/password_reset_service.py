from rest_framework.exceptions import ValidationError
from app.accounts.models import User
from services.otp_service import (
    generate_otp, store_otp, verify_otp, increment_attempts, create_reset_token, 
    get_userid_for_reset_token, delete_reset_token,
)
from services.notification_services import send_email_otp_async, send_sms_otp


def request_password_reset(*, kind, identifier):
    attempts = increment_attempts(f"password_request:{kind}", identifier=identifier, window_seconds=60)
    if attempts > 5:
        raise ValidationError("Too many OTP requests. Try again later.")
    try:
        user = (
            User.objects.get(email=identifier) if kind == "email"
            else User.objects.get(phone_no=identifier)
        )
        if kind == "email" and not user.is_email_verified:
            raise ValidationError("Email ID not verified. Please verify your email id first.")
        elif kind == "phone" and not user.is_phone_verified:
            raise ValidationError("Phone number not verified. Please verify your phone number first.")
        
    except User.DoesNotExist:
        raise ValidationError("User does not exist. Please register.")
    
    otp = generate_otp()
    store_otp(f"password:{kind}", identifier, otp)

    if kind == "email":
        send_email_otp_async(identifier, otp)
    else:
        send_sms_otp(identifier, otp)


def verify_password_reset_otp(*, kind, identifier, otp):
    attempts = increment_attempts(f"password_verify:{kind}", identifier, 300)
    if attempts > 5:
        raise ValidationError("Too many attempts")

    if not verify_otp(f"password:{kind}", identifier, otp):
        raise ValidationError("Invalid OTP")

    user = (
        User.objects.get(email=identifier)
        if kind == "email"
        else User.objects.get(phone_no=identifier)
    )
    return create_reset_token(user.id)


def reset_password(*, reset_token, new_password):
    user_id = get_userid_for_reset_token(reset_token)
    if not user_id:
        raise ValidationError("Invalid or expired reset token")

    user = User.objects.get(pk=user_id)
    user.set_password(new_password)
    user.save(update_fields=["password"])

    delete_reset_token(reset_token)
