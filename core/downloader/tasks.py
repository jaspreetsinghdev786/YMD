# ============================================================================
# core/downloader/tasks.py
# ============================================================================
import logging

from celery import shared_task
from django.db import transaction, connection, close_old_connections

logger = logging.getLogger("downloader")


@shared_task(
    bind=True,
    ignore_result=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=3600,
    soft_time_limit=3300,
)
def download_task(self, download_id: int):
    logger.info(f"Task started: download_id={download_id}")

    try:
        close_old_connections()

        from .models import Download
        from .services import DownloadService, clean_error_msg

        use_locking = connection.vendor != "sqlite"

        with transaction.atomic():
            qs = Download.objects.filter(id=download_id)
            if use_locking:
                qs = qs.select_for_update()

            download = qs.get()

            if download.status not in ("queued", "failed"):
                logger.warning(f"Download {download_id} already {download.status}, skipping")
                return {"status": "skipped"}

            download.status = "downloading"
            download.progress = 5
            download.save(update_fields=["status", "progress", "updated_at"])

        service = DownloadService(download)
        success = service.execute()

        download.refresh_from_db()

        if success:
            logger.info(f"Download {download_id} completed: {download.file_path}")
        else:
            logger.error(f"Download {download_id} failed: {download.error}")

        return {
            "status": download.status,
            "file_path": download.file_path,
            "error": download.error,
            "progress": download.progress,
        }

    except Exception as e:
        from .models import Download
        from .services import clean_error_msg

        msg = clean_error_msg(e)
        logger.exception(f"Task exception for download {download_id}: {msg}")

        try:
            Download.objects.filter(id=download_id).update(
                status="failed",
                progress=0,
                error=f"Task error: {msg[:200]}",
            )
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "failed", "error": msg[:200]}

    finally:
        close_old_connections()
