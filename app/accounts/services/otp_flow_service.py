from rest_framework.exceptions import ValidationError
from services.otp_service import (
    generate_otp,
    store_otp,
    verify_otp,
    increment_attempts,
)
from services.notification_services import send_sms_otp, send_email_otp_async
from core.utils import get_user


MAX_ATTEMPTS = 5


def send_otp(*, kind, identifier, purpose):
    otp = generate_otp()
    store_otp(f"{purpose}:{kind}", identifier, otp)

    if kind == "email":
        send_email_otp_async(identifier, otp)
    elif kind == "phone":
        send_sms_otp(identifier, otp)
    else:
        raise ValidationError("Invalid kind")


def verify_otp_flow(*, kind, identifier, otp, purpose):
    attempts = increment_attempts(
        f"{purpose}:{kind}",
        identifier,
        window_seconds=300,
    )
    if attempts > MAX_ATTEMPTS:
        raise ValidationError("Too many attempts. Try later.")

    ok = verify_otp(f"{purpose}:{kind}", identifier, otp)
    if not ok:
        raise ValidationError("Invalid or expired OTP")
