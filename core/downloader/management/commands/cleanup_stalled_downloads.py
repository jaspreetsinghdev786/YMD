from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from downloader.models import Download


class Command(BaseCommand):
    help = "Fail stalled downloads that are stuck in downloading state"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
            help="Minutes after which a downloading job is considered stalled"
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        cutoff = timezone.now() - timedelta(minutes=minutes)

        count = Download.objects.filter(
            status="downloading",
            updated_at__lt=cutoff
        ).update(
            status="failed",
            error="Stalled download (auto-cleaned)"
        )

        self.stdout.write(
            self.style.SUCCESS(f"Cleaned {count} stalled downloads")
        )
