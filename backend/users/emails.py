import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token

logger = logging.getLogger(__name__)


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _send(subject, body, to):
    # A mail server problem must not break registration; the user can request a new email.
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:
        logger.exception("Failed to send email to %s", to)


def send_verification_email(user):
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email?uid={_uid(user)}&token={token}"
    name = user.first_name or "there"
    _send(
        "Verify your email address",
        f"Hi {name},\n\nPlease confirm your email address:\n\n{link}\n\n"
        "If you did not create an account, you can ignore this message.\n",
        user.email,
    )


def send_password_reset_email(user):
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={_uid(user)}&token={token}"
    name = user.first_name or "there"
    _send(
        "Reset your password",
        f"Hi {name},\n\nUse this link to choose a new password:\n\n{link}\n\n"
        "If you did not ask for this, you can ignore this message.\n",
        user.email,
    )
