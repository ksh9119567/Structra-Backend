# accounts/services/notification_service.py
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email_otp(email: str, otp: str, ttl_minutes: int = 5):
    """Send OTP via email with error handling."""
    subject = "Your verification code"
    message = f"Your verification code is {otp}. It will expire in {ttl_minutes} minutes."
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        logger.info(f"OTP email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        # In development, this is acceptable; in production, you might queue for retry
        raise


# SMS placeholder: implement with Twilio or provider later
def send_sms_otp(phone_number: str, otp: str, ttl_minutes: int = 5):
    """Send OTP via SMS with error handling."""
    try:
        # TODO: integrate with Twilio or other SMS provider; for development, log it
        logger.info(f"[SMS] Send OTP {otp} to phone {phone_number} (expires in {ttl_minutes} min)")
        # Example: send_email_otp(f"{phone_number}@sms-gateway.example", otp)
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {phone_number}: {str(e)}")
        raise
