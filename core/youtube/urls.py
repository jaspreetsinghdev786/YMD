from django.urls import path
from .views import (
    YouTubeValidateView, 
    YouTubeSearchView,
    PlaylistDetailView
)

urlpatterns = [
    path("validate/", YouTubeValidateView.as_view(), name="youtube-validate"),
    path("search/", YouTubeSearchView.as_view(), name="youtube-search"),
    path("playlist/details/", PlaylistDetailView.as_view(), name="playlist-details"),
]