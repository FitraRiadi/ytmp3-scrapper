from django.urls import include, path, re_path

from api import views

urlpatterns = [
    path("api/", include("api.urls")),
    # semua path lain -> React SPA (hasil build Vite)
    re_path(r"^(?!api/)(?P<path>.*)$", views.spa),
]
