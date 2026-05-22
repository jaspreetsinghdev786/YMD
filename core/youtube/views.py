from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    YouTubeURLSerializer, 
    YouTubeSearchSerializer,
    PlaylistDetailSerializer
)
from .utils import (
    get_video_id, 
    get_playlist_id, 
    fetch_video_metadata, 
    fetch_playlist_metadata,
    search_youtube
)
from rest_framework.permissions import IsAuthenticated

class YouTubeValidateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = YouTubeURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]
        
        video_id = get_video_id(url)
        playlist_id = get_playlist_id(url)
        
        if video_id:
            metadata = fetch_video_metadata(video_id)
            if not metadata:
                return Response(
                    {"error": "Invalid video"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({"type": "video", "metadata": metadata})
        
        elif playlist_id:
            # By default, don't include all videos in validate endpoint
            metadata = fetch_playlist_metadata(playlist_id, include_videos=False)
            if not metadata:
                return Response(
                    {"error": "Invalid playlist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({"type": "playlist", "metadata": metadata})
        
        else:
            return Response(
                {"error": "Invalid YouTube URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class YouTubeSearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = YouTubeSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data["query"]
        search_type = serializer.validated_data["search_type"]
        max_results = serializer.validated_data["max_results"]
        
        try:
            results = search_youtube(query, search_type, max_results)
            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Search failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PlaylistDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PlaylistDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        playlist_id = serializer.validated_data["playlist_id"]
        include_videos = serializer.validated_data["include_videos"]
        max_results = serializer.validated_data["max_results"]
        
        try:
            metadata = fetch_playlist_metadata(
                playlist_id, 
                include_videos=include_videos,
                max_results=max_results
            )
            if not metadata:
                return Response(
                    {"error": "Invalid playlist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(metadata, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch playlist: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )