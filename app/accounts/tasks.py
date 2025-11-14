# accounts/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


@shared_task(bind=True)
def send_otp_email_task(self, email: str, otp: str, subject: str = "Your verification code"):
    """
    Celery task to send an email containing OTP.
    """
    try:
        message = render_to_string("accounts/email/otp.txt", {"otp": otp})
        html_message = render_to_string("accounts/email/otp.html", {"otp": otp})
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return {"status": "sent", "email": email}
    except Exception as exc:
        # Optionally retry a couple times
        raise self.retry(exc=exc, countdown=10, max_retries=3)
