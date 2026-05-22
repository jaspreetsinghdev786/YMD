from googleapiclient.discovery import build
from django.conf import settings
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Regex to extract video ID or playlist ID
# Supports: youtube.com, music.youtube.com, youtu.be, /shorts/, /embed/
VIDEO_REGEX = r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})"
PLAYLIST_REGEX = r"(?:list=)([a-zA-Z0-9_-]+)"

# YouTube Music domains that need to be normalised
_YOUTUBE_MUSIC_HOSTS = {"music.youtube.com", "m.music.youtube.com"}


def normalize_youtube_url(url: str) -> str:
    """
    Convert music.youtube.com (YouTube Music) URLs to www.youtube.com
    so the YouTube Data API can resolve them correctly.
    YouTube Music uses the same video/playlist IDs as regular YouTube.
    """
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        bare = host[4:] if host.startswith("www.") else host

        if bare in _YOUTUBE_MUSIC_HOSTS:
            qs = parse_qs(parsed.query)
            kept = {k: qs[k][0] for k in ("v", "list", "index") if k in qs}
            if not kept:
                return urlunparse(parsed._replace(netloc="www.youtube.com"))
            path = "/playlist" if "list" in kept and "v" not in kept else "/watch"
            return urlunparse(parsed._replace(
                netloc="www.youtube.com",
                path=path,
                query=urlencode(kept),
            ))
    except Exception:
        pass
    return url


def get_video_id(url: str):
    """
    Extract the YouTube video ID from any supported URL format,
    including music.youtube.com links.
    """
    url = normalize_youtube_url(url)
    try:
        qs = parse_qs(urlparse(url).query)
        if "v" in qs:
            return qs["v"][0]
    except Exception:
        pass
    match = re.search(VIDEO_REGEX, url)
    return match.group(1) if match else None


def get_playlist_id(url: str):
    """Extract the YouTube playlist ID from any supported URL format."""
    match = re.search(PLAYLIST_REGEX, url)
    return match.group(1) if match else None


def fetch_video_metadata(video_id):
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    if not response["items"]:
        return None
    item = response["items"][0]
    snippet = item["snippet"]
    content = item["contentDetails"]
    stats = item.get("statistics", {})

    return {
        "id": video_id,
        "title": snippet["title"],
        "description": snippet["description"],
        "channel": snippet["channelTitle"],
        "channel_id": snippet["channelId"],
        "published_at": snippet["publishedAt"],
        "duration": content["duration"],
        "thumbnails": snippet["thumbnails"],
        "view_count": stats.get("viewCount", "0"),
        "like_count": stats.get("likeCount", "0"),
        "comment_count": stats.get("commentCount", "0"),
    }


def fetch_playlist_metadata(playlist_id, include_videos=True, max_results=500):
    """
    Fetch playlist metadata with optional video details.
    """
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        id=playlist_id
    )
    response = request.execute()

    if not response["items"]:
        return None

    item = response["items"][0]
    snippet = item["snippet"]
    content = item["contentDetails"]

    playlist_data = {
        "id": playlist_id,
        "title": snippet["title"],
        "description": snippet["description"],
        "channel": snippet["channelTitle"],
        "channel_id": snippet["channelId"],
        "published_at": snippet["publishedAt"],
        "item_count": content["itemCount"],
        "thumbnails": snippet["thumbnails"],
    }

    if include_videos:
        videos = []
        next_page_token = None

        while True:
            playlist_items_request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=max_results,
                pageToken=next_page_token
            )
            playlist_items_response = playlist_items_request.execute()

            for video_item in playlist_items_response["items"]:
                video_snippet = video_item["snippet"]
                video_content = video_item["contentDetails"]

                videos.append({
                    "video_id": video_content["videoId"],
                    "title": video_snippet["title"],
                    "description": video_snippet["description"],
                    "channel": video_snippet.get("videoOwnerChannelTitle", snippet["channelTitle"]),
                    "published_at": video_snippet["publishedAt"],
                    "thumbnails": video_snippet["thumbnails"],
                    "position": video_snippet["position"],
                })

            next_page_token = playlist_items_response.get("nextPageToken")
            if not next_page_token:
                break

        playlist_data["videos"] = videos
        playlist_data["videos_fetched"] = len(videos)

    return playlist_data


def search_youtube(query, search_type="video", max_results=20):
    request = youtube.search().list(
        part="snippet",
        q=query,
        type=search_type,
        maxResults=max_results,
        order="relevance"
    )
    response = request.execute()

    results = []
    for item in response["items"]:
        snippet = item["snippet"]

        result_data = {
            "title": snippet["title"],
            "description": snippet["description"],
            "channel": snippet["channelTitle"],
            "channel_id": snippet["channelId"],
            "published_at": snippet["publishedAt"],
            "thumbnails": snippet["thumbnails"],
        }

        if search_type == "video":
            result_data["video_id"] = item["id"]["videoId"]
            result_data["type"] = "video"
        elif search_type == "playlist":
            result_data["playlist_id"] = item["id"]["playlistId"]
            result_data["type"] = "playlist"
        elif search_type == "channel":
            result_data["channel_id"] = item["id"]["channelId"]
            result_data["type"] = "channel"

        results.append(result_data)

    return {
        "query": query,
        "search_type": search_type,
        "result_count": len(results),
        "results": results
    }
