import logging

from rest_framework.exceptions import ValidationError

from services.otp_service import (
    generate_otp,
    store_otp,
    verify_otp,
    increment_attempts,
)
from services.notification_services import send_sms_otp, send_email_otp_async

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


def send_otp(*, kind, identifier, purpose):
    logger.info(f"Sending OTP for {kind}: {identifier}, purpose: {purpose}")
    otp = generate_otp()
    store_otp(f"{purpose}:{kind}", identifier, otp)

    if kind == "email":
        send_email_otp_async(identifier, otp)
    elif kind == "phone":
        send_sms_otp(identifier, otp)
    else:
        logger.error(f"Invalid kind specified: {kind}")
        raise ValidationError("Invalid kind")
    logger.info(f"OTP sent successfully for {kind}: {identifier}")


def verify_otp_flow(*, kind, identifier, otp, purpose):
    logger.info(f"Verifying OTP for {kind}: {identifier}, purpose: {purpose}")
    attempts = increment_attempts(
        f"{purpose}:{kind}",
        identifier,
        window_seconds=300,
    )
    if attempts > MAX_ATTEMPTS:
        logger.warning(f"Too many OTP attempts for {kind}: {identifier}")
        raise ValidationError("Too many attempts. Try later.")

    ok = verify_otp(f"{purpose}:{kind}", identifier, otp)
    if not ok:
        logger.warning(f"Invalid or expired OTP for {kind}: {identifier}")
        raise ValidationError("Invalid or expired OTP")
    logger.info(f"OTP verified successfully for {kind}: {identifier}")
