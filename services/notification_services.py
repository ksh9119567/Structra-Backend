import logging
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.core.mail import send_mail
from django.conf import settings

from app.accounts.tasks import send_otp_email_task 

logger = logging.getLogger(__name__)


# for synchronous sending
def send_email_otp(recipient_email, otp) -> bool:
    import ipdb; ipdb.set_trace()
    sender_email = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD
    host = settings.EMAIL_HOST
    port = settings.EMAIL_PORT

    # Subject and headers
    msg = MIMEMultipart("alternative")
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = 'Your One-Time Password (OTP)'

    # Plain text fallback
    text = f"""\
Hello,

Your One-Time Password (OTP) is: {otp}

This OTP is valid for the next 5 minutes.

If you did not request this, please ignore the email.
"""

    # HTML template body
    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <p>Hello,</p>
    <p>Your One-Time Password (OTP) is:</p>
    <h1 style="color: #000080;">{otp}</h1>
    <p>This OTP is valid for <strong>5 minutes</strong>.</p>
    <p>If you did not request this, please ignore this email.</p>
    <br>
    <p>Regards,<br>Team TaxSpanner</p>
</body>
</html>
"""

    # Attach both plain and HTML parts
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        logger.info("Email sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

# for asynchronous sending
def send_email_otp_async(email: str, otp: str, subject: str = "Your verification code"):
    # call the celery task (non-blocking)
    send_otp_email_task.delay(email, otp, subject)


def send_sms_otp(phone_number: str, otp: str, ttl_minutes: int = 5):
    """Send OTP via SMS with error handling."""
    try:
        # TODO: integrate with Twilio or other SMS provider; for development, log it
        logger.info(f"[SMS] Send OTP {otp} to phone {phone_number} (expires in {ttl_minutes} min)")
        # Example: send_email_otp(f"{phone_number}@sms-gateway.example", otp)
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {phone_number}: {str(e)}")
        raise
