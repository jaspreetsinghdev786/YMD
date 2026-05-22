# ============================================================================
# core/downloader/urls.py - URL Configuration
# ============================================================================
from django.urls import path
from . import views

app_name = 'downloader'

urlpatterns = [
    path('create/', views.create_download, name='create'),
    path('status/<int:download_id>/', views.download_status, name='status'),
    path('file/<int:download_id>/', views.download_file, name='file'),
    path('list/', views.list_downloads, name='list'),
    path('delete/<int:download_id>/', views.delete_download, name='delete'),
    path('queue/', views.queue_list, name='queue'),
]