# ============================================================================
# core/downloader/views.py - Complete API Views (FIXED)
# ============================================================================
import logging
from pathlib import Path
from celery import current_app as celery_app
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Download
from .serializers import DownloadCreateSerializer, DownloadSerializer,QueueSerializer
from .tasks import download_task
from kombu.utils.uuid import uuid

logger = logging.getLogger('downloader')




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_download(request):
    """
    OPTIMIZED: Create a new download job in ~200ms
    
    POST /api/downloader/create/
    Body: {
        "url": "https://youtube.com/watch?v=...",
        "format": "mp3|mp4",
        "quality": "best"
    }
    """
    serializer = DownloadCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        logger.warning(
            f"Invalid download request from {request.user}: "
            f"{serializer.errors}"
        )
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # âœ¨ OPTIMIZATION 1: Pre-generate task_id (no broker round-trip)
        task_id = uuid()
        
        # âœ¨ OPTIMIZATION 2: Single database write with all fields
        download = Download.objects.create(
            user=request.user,
            url=serializer.validated_data['url'],
            format=serializer.validated_data['format'],
            quality=serializer.validated_data.get('quality', 'best'),
            status='queued',
            progress=0,
            celery_task_id=task_id  # Set immediately - no second save()
        )
        
        # âœ¨ OPTIMIZATION 3: Non-blocking fire-and-forget task submission
        download_task.apply_async(
            args=[download.id],
            task_id=task_id,
            ignore_result=True,
            compression='gzip',
            serializer='json'
        )
        
        logger.info(
            f"âœ… Download {download.id} created by {request.user} - "
            f"Task: {task_id}"
        )
        
        # âœ¨ OPTIMIZATION 4: Manual response dict (no serializer overhead)
        return Response(
            {
                'id': download.id,
                'url': download.url,
                'format': download.format,
                'quality': download.quality,
                'quality_actual': None,
                'status': 'queued',
                'progress': 0,
                'file_path': None,
                'file_url': None,
                'error': None,
                'celery_task_id': task_id,
                'created_at': download.created_at.isoformat(),
                'updated_at': download.updated_at.isoformat()
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.exception(f"Error creating download for {request.user}")
        return Response(
            {'error': 'Failed to create download', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_status(request, download_id):
    """
    Get download status
    
    GET /api/downloader/status/<id>/
    
    Response: {
        "id": 1,
        "url": "...",
        "status": "downloading",
        "progress": 45,
        ...
    }
    """
    try:
        download = Download.objects.get(id=download_id, user=request.user)
        return Response(DownloadSerializer(download).data)
        
    except Download.DoesNotExist:
        logger.warning(
            f"Download {download_id} not found for user {request.user}"
        )
        return Response(
            {'error': 'Download not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_file(request, download_id):
    """
    Download the completed file
    
    GET /api/downloader/file/<id>/
    
    Returns: File download (MP3/MP4/ZIP)
    """
    try:
        download = Download.objects.get(id=download_id, user=request.user)
        
        if download.status != 'completed':
            return Response(
                {
                    'error': 'Download not completed',
                    'status': download.status,
                    'progress': download.progress
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not download.file_path:
            return Response(
                {'error': 'File path not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        file_path = Path(settings.MEDIA_ROOT) / download.file_path
        
        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            return Response(
                {'error': 'File not found on server'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Determine content type
        content_type = 'audio/mpeg' if download.format == 'mp3' else 'video/mp4'
        if file_path.suffix == '.zip':
            content_type = 'application/zip'
        
        logger.info(
            f"ðŸ“¥ User {request.user} downloading file: {file_path.name}"
        )
        
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=file_path.name
        )
        return response
        
    except Download.DoesNotExist:
        raise Http404("Download not found")
    except Exception as e:
        logger.exception(f"Error serving file for download {download_id}")
        return Response(
            {'error': 'Failed to serve file', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
import os
import logging
from urllib.parse import parse_qs, urlparse
from googleapiclient.discovery import build
import re


logger = logging.getLogger(__name__)


def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    if not url:
        return None
    
    parsed_url = urlparse(url)
    
    # Handle youtu.be and shorts URLs
    if parsed_url.netloc.lower() in ['youtu.be', 'www.youtu.be'] or \
       parsed_url.path.lower().startswith('/shorts'):
        video_id = parsed_url.path.split('/')[-1]
        return video_id if len(video_id) == 11 else None
    
    # Handle standard YouTube URLs
    if 'youtube.com' in parsed_url.netloc.lower():
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if video_id and len(video_id) == 11:
            return video_id
    
    return None


def get_youtube_videos_batch(video_ids):
    """
    Fetch multiple YouTube videos in a SINGLE API call (up to 50 videos)
    Returns dict mapping video_id -> video_data
    """
    if not video_ids:
        return {}
    
    try:
        api_key = os.getenv('YOUTUBE_API_KEY') or settings.YOUTUBE_API_KEY
        
        if not api_key:
            logger.warning("YouTube API key not found")
            return {}
        
        # Build YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Batch request with comma-separated IDs (max 50)
        video_ids_str = ','.join(video_ids[:50])
        
        request = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_ids_str
        )
        response = request.execute()
        
        # Map video_id -> data
        results = {}
        for item in response.get('items', []):
            video_id = item['id']
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            results[video_id] = {
                'id': video_id,
                'title': snippet.get('title'),
                'description': snippet.get('description'),
                'channel': snippet.get('channelTitle'),
                'channel_id': snippet.get('channelId'),
                'published_at': snippet.get('publishedAt'),
                'duration': content_details.get('duration'),
                'thumbnails': snippet.get('thumbnails', {}),
                'view_count': statistics.get('viewCount'),
                'like_count': statistics.get('likeCount'),
                'comment_count': statistics.get('commentCount')
            }
        
        return results
        
    except Exception as e:
        logger.error(f"YouTube API batch error: {str(e)}")
        return {}


def get_cached_youtube_data(video_id):
    """Get YouTube data from cache or return None"""
    cache_key = f'youtube_video_{video_id}'
    return cache.get(cache_key)


def set_cached_youtube_data(video_id, data, timeout=86400):
    """Cache YouTube data for 24 hours (86400 seconds)"""
    cache_key = f'youtube_video_{video_id}'
    cache.set(cache_key, data, timeout)


def format_file_size(bytes_size):
    """Convert bytes to human-readable format"""
    if not bytes_size:
        return "0B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"


def format_duration(duration_str):
    """Convert ISO 8601 duration (PT2M59S) to readable format (2:59)"""
    if not duration_str or not duration_str.startswith('PT'):
        return "0:00"
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    return "0:00"


class DownloadSerializer(serializers.ModelSerializer):
    """Optimized serializer with batched YouTube API calls"""
    youtube_data = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_size_bytes = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    format_quality = serializers.SerializerMethodField()
    
    class Meta:
        model = Download
        fields = [
            'id', 'url', 'format', 'quality', 'quality_actual', 
            'status', 'progress', 'file_path', 'file_url', 
            'error', 'created_at', 'updated_at',
            'youtube_data', 'file_size', 'file_size_bytes',
            'formatted_date', 'thumbnail', 'title', 
            'channel_name', 'duration', 'format_quality'
        ]
    
    def get_youtube_metadata(self, obj):
        """
        Get YouTube metadata from pre-fetched context data
        This is called multiple times but uses cached context data
        """
        # Get from serializer context (pre-fetched in view)
        youtube_cache = self.context.get('youtube_metadata', {})
        video_id = extract_youtube_id(obj.url)
        
        if not video_id:
            return None
        
        return youtube_cache.get(video_id)
    
    def get_youtube_data(self, obj):
        """Return full YouTube data for compatibility"""
        metadata = self.get_youtube_metadata(obj)
        
        if metadata:
            return {
                "type": "video",
                "metadata": metadata
            }
        
        return None
    
    def get_file_size(self, obj):
        """Get formatted file size from pre-computed context"""
        file_sizes = self.context.get('file_sizes', {})
        return file_sizes.get(obj.id, {}).get('formatted', '0B')
    
    def get_file_size_bytes(self, obj):
        """Get raw file size from pre-computed context"""
        file_sizes = self.context.get('file_sizes', {})
        return file_sizes.get(obj.id, {}).get('bytes', 0)
    
    def get_formatted_date(self, obj):
        """Format date as 'Jan 3, 2026'"""
        if obj.updated_at:
            return obj.updated_at.strftime('%b %d, %Y')
        return obj.created_at.strftime('%b %d, %Y')
    
    def get_thumbnail(self, obj):
        """Get highest quality video thumbnail URL"""
        metadata = self.get_youtube_metadata(obj)
        
        if metadata:
            thumbnails = metadata.get('thumbnails', {})
            
            for quality in ['maxres', 'high', 'medium', 'default']:
                if quality in thumbnails:
                    return thumbnails[quality].get('url')
        
        return None
    
    def get_title(self, obj):
        """Get video title from YouTube API"""
        metadata = self.get_youtube_metadata(obj)
        
        if metadata and metadata.get('title'):
            return metadata['title']
        
        # Fallback to filename
        if obj.file_path:
            filename = os.path.basename(obj.file_path)
            name = os.path.splitext(filename)[0]
            return name.replace('_', ' ').replace('-', ' ')
        
        return 'Unknown Video'
    
    def get_channel_name(self, obj):
        """Get channel name from YouTube API"""
        metadata = self.get_youtube_metadata(obj)
        
        if metadata and metadata.get('channel'):
            return metadata['channel']
        
        return 'Unknown Creator'
    
    def get_duration(self, obj):
        """Get formatted duration from YouTube API"""
        metadata = self.get_youtube_metadata(obj)
        
        if metadata and metadata.get('duration'):
            return format_duration(metadata['duration'])
        
        return "0:00"
    
    def get_format_quality(self, obj):
        """Get formatted quality string"""
        format_upper = obj.format.upper() if obj.format else 'UNKNOWN'
        quality = obj.quality_actual or obj.quality or 'BEST'
        
        if format_upper == 'MP3':
            return f"{format_upper} {quality.upper()}"
        else:
            quality_str = quality.upper()
            if quality_str.isdigit():
                return f"{format_upper} {quality_str}P"
            return f"{format_upper} {quality_str}"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_downloads(request):
    """
    Optimized endpoint with batched YouTube API calls and optional pagination
    
    GET /api/downloader/list/  -> Returns ALL downloads
    GET /api/downloader/list/?limit=20  -> Returns 20 per page
    """
    # Base queryset
    all_downloads = Download.objects.filter(user=request.user)
    
    # ============ STATISTICS ============
    total_downloads = all_downloads.count()
    
    now = timezone.now()
    downloads_this_month = all_downloads.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).count()
    
    # Calculate storage (optimized with values_list)
    storage_bytes = 0
    file_paths = all_downloads.filter(
        status='completed'
    ).exclude(file_path__isnull=True).values_list('file_path', flat=True)
    
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                storage_bytes += os.path.getsize(file_path)
            except OSError:
                pass
    
    storage_used = format_file_size(storage_bytes)
    
    # ============ FILTERING ============
    downloads = all_downloads.order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        downloads = downloads.filter(status=status_filter)
    
    format_filter = request.GET.get('format')
    if format_filter:
        downloads = downloads.filter(format__iexact=format_filter)
    
    # ============ PAGINATION (OPTIONAL) ============
    page = int(request.GET.get('page', 1))
    limit = request.GET.get('limit')
    
    # If limit is not specified, return all results
    if limit is None:
        total_count = downloads.count()
        total_pages = 1
        downloads_page = list(downloads)
        logger.info(f"ðŸ“‹ Returning ALL {total_count} downloads (no pagination)")
    else:
        limit = int(limit)
        total_count = downloads.count()
        total_pages = (total_count + limit - 1) // limit
        
        offset = (page - 1) * limit
        downloads_page = list(downloads[offset:offset + limit])
        logger.info(f"ðŸ“‹ Returning page {page}/{total_pages} with {len(downloads_page)} downloads")
    
    # ============ BATCH OPTIMIZATION ============
    # 1. Extract all video IDs
    video_ids_needed = []
    video_id_map = {}  # download.id -> video_id
    
    for download in downloads_page:
        video_id = extract_youtube_id(download.url)
        if video_id:
            video_ids_needed.append(video_id)
            video_id_map[download.id] = video_id
    
    # 2. Check cache for existing data
    youtube_metadata = {}
    uncached_ids = []
    
    for video_id in video_ids_needed:
        cached_data = get_cached_youtube_data(video_id)
        if cached_data:
            youtube_metadata[video_id] = cached_data
        else:
            uncached_ids.append(video_id)
    
    # 3. Batch fetch uncached videos in chunks of 50
    if uncached_ids:
        logger.info(f"ðŸ”„ Fetching {len(uncached_ids)} uncached videos from YouTube API")
        
        # Process in batches of 50 (YouTube API limit)
        for i in range(0, len(uncached_ids), 50):
            batch = uncached_ids[i:i+50]
            batch_results = get_youtube_videos_batch(batch)
            
            # Cache results for 24 hours
            for video_id, data in batch_results.items():
                set_cached_youtube_data(video_id, data, timeout=86400)
                youtube_metadata[video_id] = data
        
        logger.info(f"âœ… Cached {len(batch_results)} new videos")
    
    # 4. Pre-compute file sizes
    file_sizes = {}
    for download in downloads_page:
        if download.file_path and os.path.exists(download.file_path):
            try:
                size_bytes = os.path.getsize(download.file_path)
                file_sizes[download.id] = {
                    'bytes': size_bytes,
                    'formatted': format_file_size(size_bytes)
                }
            except OSError:
                file_sizes[download.id] = {'bytes': 0, 'formatted': '0B'}
        else:
            file_sizes[download.id] = {'bytes': 0, 'formatted': '0B'}
    
    # ============ SERIALIZATION ============
    serializer = DownloadSerializer(
        downloads_page, 
        many=True,
        context={
            'request': request,
            'youtube_metadata': youtube_metadata,  # Pre-fetched data
            'file_sizes': file_sizes  # Pre-computed sizes
        }
    )
    
    logger.info(
        f"ðŸ“‹ User {request.user} - Returned {len(serializer.data)} downloads "
        f"({len(uncached_ids)} API calls, {len(youtube_metadata) - len(uncached_ids)} cached)"
    )
    
    return Response({
        # Statistics
        'total_downloads': total_downloads,
        'downloads_this_month': downloads_this_month,
        'storage_used': storage_used,
        'storage_used_bytes': storage_bytes,
        
        # Pagination
        'count': len(serializer.data),
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'has_next': page < total_pages,
        'has_previous': page > 1,
        
        # Downloads with YouTube metadata
        'downloads': serializer.data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_download(request, download_id):
    """
    Delete a download record and its file
    
    DELETE /api/downloader/delete/<id>/
    
    Returns: 204 No Content
    """
    try:
        download = Download.objects.get(id=download_id, user=request.user)
        
        # Delete file if exists
        if download.file_path:
            file_path = Path(settings.MEDIA_ROOT) / download.file_path
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"ðŸ—‘ï¸ Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
        
        # Delete record
        download.delete()
        logger.info(
            f"ðŸ—‘ï¸ Download {download_id} deleted by {request.user}"
        )
        
        return Response(
            {'message': 'Download deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
        
    except Download.DoesNotExist:
        return Response(
            {'error': 'Download not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error deleting download {download_id}")
        return Response(
            {'error': 'Failed to delete download', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




def _get_celery_active_task_ids():
    """
    Use Celery inspect to collect active/reserved/scheduled task ids from workers.
    Returns a set of task_id strings. If inspect fails or returns None, returns an empty set.
    """
    try:
        insp = celery_app.control.inspect(timeout=1.0)
        if not insp:
            return set()

        task_ids = set()

        for method in ("active", "reserved", "scheduled"):
            data = getattr(insp, method)()
            if not data:
                continue
            for worker, tasks in data.items():
                if not tasks:
                    continue
                for t in tasks:
                    # task dict shapes vary by worker version; try common keys
                    tid = t.get("id") or t.get("request", {}).get("id")
                    if tid:
                        task_ids.add(tid)
        return task_ids
    except Exception:
        # If Celery not running / unreachable -> treat as no active tasks
        return set()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queue_list(request):
    """
    USER-SPECIFIC queue:
    - Only the authenticated user's downloads
    - Only active states: queued + downloading
    """
    queue = (
        Download.objects
        .filter(
            user=request.user,              # 🔐 USER ISOLATION
            status__in=['queued', 'downloading']
        )
        .order_by('created_at')
    )

    serializer = QueueSerializer(queue, many=True)

    return Response({
        'count': queue.count(),
        'queue': serializer.data
    })
