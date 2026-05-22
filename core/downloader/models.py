# ============================================================================
# core/downloader/models.py - Download Model (OPTIMIZED)
# ============================================================================
from django.db import models
from django.conf import settings
from django.utils import timezone


class Download(models.Model):
    """
    Model to track YouTube download jobs
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FORMAT_CHOICES = [
        ('mp3', 'MP3 Audio'),
        ('mp4', 'MP4 Video'),
    ]
    
    # Core fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='downloads'
    )
    url = models.URLField(max_length=500)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    quality = models.CharField(max_length=10, default='best')
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='queued'
    )
    progress = models.IntegerField(default=0)  # 0-100
    
    # Result fields
    file_path = models.CharField(max_length=500, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    
    # Metadata
    quality_actual = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Actual quality downloaded"
    )
    celery_task_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Celery task ID"
    )
    title = models.CharField(
    max_length=500,
    blank=True,
    null=True,
    db_index=True)
    channel_name = models.CharField(max_length=255, blank=True, null=True)
    duration = models.PositiveIntegerField(default=0)


    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'downloader_downloads'
        ordering = ['-created_at']
        indexes = [
            # Existing indexes
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
            
            # âœ¨ NEW: Optimized indexes for performance
            models.Index(fields=['celery_task_id'], name='idx_celery_task'),
            models.Index(fields=['user', '-created_at'], name='idx_user_created'),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.format} - {self.status}"
    
    @property
    def is_complete(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def is_in_progress(self):
        return self.status in ['queued', 'downloading']
    
    @property
    def file_url(self):
        if self.file_path:
            return f"{settings.MEDIA_URL}{self.file_path}"
        return None
