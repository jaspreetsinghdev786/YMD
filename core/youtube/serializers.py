from rest_framework import serializers

class YouTubeURLSerializer(serializers.Serializer):
    url = serializers.URLField()

class YouTubeSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=200)
    search_type = serializers.ChoiceField(
        choices=["video", "playlist", "channel"],
        default="video"
    )
    max_results = serializers.IntegerField(min_value=1, max_value=50, default=10)

class PlaylistDetailSerializer(serializers.Serializer):
    playlist_id = serializers.CharField(max_length=100)
    include_videos = serializers.BooleanField(default=True)
    max_results = serializers.IntegerField(min_value=1, max_value=50, default=50)