from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = "Test sending email via Gmail SMTP"

    def handle(self, *args, **kwargs):
        send_mail(
            "Test Email from YMD",
            "If you receive this email, Gmail SMTP is working!",
            settings.DEFAULT_FROM_EMAIL,
            ["gamerramgarhia295@gmail.com"],  # replace with your test email
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS("Email sent successfully!"))
