from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("media", views.MediaAssetViewSet, basename="media")

urlpatterns = [
    path("media/<uuid:pk>/<slug:variant>/", views.MediaServeView.as_view(), name="media_serve"),
    path("", include(router.urls)),
]
