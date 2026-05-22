# ============================================================================
# core/downloader/admin.py - Django Admin Interface
# ============================================================================
from django.contrib import admin
from .models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'format',
        'quality',
        'quality_actual',
        'status',
        'progress',
        'created_at'
    ]
    list_filter = ['status', 'format', 'quality', 'created_at']
    search_fields = ['url', 'user', 'error', 'file_path']
    readonly_fields = [
        'created_at',
        'updated_at',
        'celery_task_id',
        'quality_actual',
        'file_url'
    ]
    
    fieldsets = (
        ('Download Info', {
            'fields': ('user', 'url', 'format', 'quality', 'quality_actual')
        }),
        ('Status', {
            'fields': ('status', 'progress', 'error')
        }),
        ('Result', {
            'fields': ('file_path', 'file_url')
        }),
        ('Technical', {
            'fields': ('celery_task_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation through admin"""
        return False
    
    def file_url(self, obj):
        """Display file URL in admin"""
        return obj.file_url
    file_url.short_description = 'File URL'