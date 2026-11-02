from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health),
    path("search", views.search),
    path("convert", views.convert),
    path("jobs", views.jobs_list),
    path("job/<str:video_id>", views.job_detail),
    path("library", views.library),
    path("library/<str:video_id>", views.library_item),
    path("media/<str:video_id>", views.media),
    path("stream/<str:video_id>", views.stream),
    path("open-folder", views.open_folder),
    path("settings", views.app_settings),
    path("settings/browse", views.settings_browse),
]
