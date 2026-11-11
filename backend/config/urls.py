from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
    path("api/v1/", include("users.urls")),
    path("api/v1/", include("uploads.urls")),
]
