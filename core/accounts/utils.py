
from django.urls import reverse
# accounts/utils.py
from django.core.mail import send_mail
from django.conf import settings

def send_verification_email(user, token):
    verify_url = f"http://127.0.0.1:8000/api/accounts/verify/{token}/"
    subject = "Verify your email - YMD"
    message = f"""
Hi {user.email},

Thank you for registering on YMD.

Please verify your email by clicking the link below:

{verify_url}

If you didn’t create this account, ignore this email.
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    """Send password reset email with reset link"""
    # Use the frontend UI URL, not the API endpoint
    reset_url = f"http://127.0.0.1:8000/reset-password/{token}/"
    subject = "Reset your password - YMD"
    message = f"""
Hi {user.email},

You have requested to reset your password for your YMD account.

Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.
Your password will remain unchanged.
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
