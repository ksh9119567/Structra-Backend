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
    except Exception as e:
        # Optionally retry a couple times
        raise self.retry(exc=e, countdown=10, max_retries=3)


@shared_task(bind=True)
def send_invite_email_task(self, email, invite_type, name, sender):
    """
    Celery task to send an invite email.
    """
    try:
        message = render_to_string("accounts/email/invite.txt", {"invite_type": invite_type, "name": name, "sender": sender})
        html_message = render_to_string("accounts/email/invite.html", {"invite_type": invite_type, "name": name, "sender": sender})
        send_mail(
            subject=f"You are invited to join {invite_type}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return {"status": "sent", "email": email}
    except Exception as e:
        # Optionally retry a couple times
        raise self.retry(exc=e, countdown=10, max_retries=3)