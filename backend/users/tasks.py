from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_email_task(subject, body, to):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])


@shared_task
def flush_expired_tokens():
    """Remove expired entries from the refresh-token blacklist tables."""
    call_command("flushexpiredtokens")
