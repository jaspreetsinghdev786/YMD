from kombu.utils.uuid import uuid
from .models import Download
from .tasks import download_task


class DownloadManager:
    """Handles creation and submission of downloads (QUEUE-SAFE)."""

    def create_download(
        self,
        user,
        url: str,
        fmt: str,
        quality: str = "best"
    ) -> Download:
        """
        Create a queued download AND enqueue Celery task
        with a known task_id so queue state is accurate.
        """
        task_id = uuid()

        download = Download.objects.create(
            user=user,
            url=url,
            format=fmt,
            quality=quality,
            status="queued",
            progress=0,
            celery_task_id=task_id,
        )

        # Fire-and-forget Celery task
        download_task.apply_async(
            args=[download.id],
            task_id=task_id,
            ignore_result=True,
            serializer="json",
            compression="gzip",
        )

        return download
def submit_download(self, download: Download):
    """
    Legacy-safe submit.
    Ensures celery_task_id exists.
    """
    if not download.celery_task_id:
        from kombu.utils.uuid import uuid
        download.celery_task_id = uuid()
        download.status = "queued"
        download.progress = 0
        download.save(
            update_fields=["celery_task_id", "status", "progress", "updated_at"]
        )

    download_task.apply_async(
        args=[download.id],
        task_id=download.celery_task_id,
        ignore_result=True,
    )
