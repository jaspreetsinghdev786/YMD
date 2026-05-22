# ============================================================================
# core/downloader/serializers.py - API Serializers
# ============================================================================
from rest_framework import serializers
from .models import Download


class DownloadCreateSerializer(serializers.Serializer):
    """Serializer for creating new downloads"""
    url = serializers.URLField(required=True)
    format = serializers.ChoiceField(choices=['mp3', 'mp4'], required=True)
    quality = serializers.CharField(required=False, default='best')
    
    def validate_url(self, value):
        """Validate YouTube URL format"""
        if 'youtube.com' not in value and 'youtu.be' not in value:
            raise serializers.ValidationError("Only YouTube URLs are supported")
        return value
    
    def validate_quality(self, value):
        """Validate quality option"""
        valid_qualities = [
            'best', '2160', '1440', '1080', '720', '480', '360',  # MP4
            'high', 'medium', 'low'  # MP3
        ]
        if value not in valid_qualities:
            raise serializers.ValidationError(
                f"Quality must be one of: {', '.join(valid_qualities)}"
            )
        return value


class DownloadSerializer(serializers.ModelSerializer):
    """Serializer for download responses"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Download
        fields = [
            'id',
            'url',
            'format',
            'quality',
            'quality_actual',
            'status',
            'progress',
            'file_path',
            'file_url',
            'error',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'status',
            'progress',
            'file_path',
            'file_url',
            'quality_actual',
            'error',
            'created_at',
            'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Get full file URL"""
        return obj.file_url
from rest_framework import serializers
from .models import Download
from urllib.parse import urlparse, parse_qs


class QueueSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    channel_name = serializers.CharField(read_only=True)  # Include channel info
    duration = serializers.IntegerField(read_only=True)   # Include duration

    class Meta:
        model = Download
        fields = [
            'id',
            'title',
            'channel_name',
            'duration',
            'status',
            'progress',
            'format',
            'quality',
            'created_at'
        ]

    def get_title(self, obj):
        """
        Get title with proper fallback chain:
        1. Database title field (set by early metadata fetch in tasks.py)
        2. Filename (for completed downloads)
        3. Video ID as last resort
        """
        # Priority 1: Use database title if available (from early metadata fetch)
        if obj.title:
            return obj.title
        
        # Priority 2: Extract from file_path if exists (completed downloads)
        if obj.file_path:
            import os
            filename = os.path.basename(obj.file_path)
            name = os.path.splitext(filename)[0]
            return name.replace('_', ' ').replace('-', ' ')
        
        # Priority 3: Extract video ID from URL as fallback
        try:
            parsed = urlparse(obj.url)
            video_id = parse_qs(parsed.query).get('v', [None])[0]
            if video_id:
                return f"Video: {video_id}"
        except Exception:
            pass
        
        # Last resort
        return "Queued download"