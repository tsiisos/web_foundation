from urllib.parse import quote

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from rest_framework import mixins, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VARIANTS, MediaAsset
from .permissions import IsEmailVerified
from .serializers import MediaAssetSerializer, MediaUploadSerializer


class MediaAssetViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MediaAssetSerializer
    parser_classes = (MultiPartParser, FormParser)

    @property
    def throttle_scope(self):
        return "upload" if self.action == "create" else None

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsEmailVerified()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return MediaAsset.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = MediaUploadSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        asset = serializer.save()
        return Response(MediaAssetSerializer(asset).data, status=201)


class MediaServeView(APIView):
    """Download a file. Public files redirect to nginx; private ones need a permission or a signed link."""

    permission_classes = [AllowAny]

    def get(self, request, pk, variant):
        if variant not in VARIANTS:
            raise Http404
        asset = get_object_or_404(MediaAsset, pk=pk)
        field = asset.thumbnail if variant == "thumbnail" else asset.file
        # 404 (not 403) for everything not allowed: do not reveal that a private file exists
        if asset.status != MediaAsset.Status.READY or not field or not self._allowed(request, asset, variant):
            raise Http404

        if asset.visibility == MediaAsset.Visibility.PUBLIC:
            return HttpResponseRedirect(field.url)

        content_type = "image/webp" if variant == "thumbnail" else asset.content_type
        response = HttpResponse(content_type=content_type)
        # "private/abc.jpg" -> "/api/protected-media/abc.jpg" (nginx internal location)
        response["X-Accel-Redirect"] = "/api/protected-media/" + quote(field.name.split("/", 1)[1])
        response["Cache-Control"] = "private, max-age=300"
        if variant == "file":
            as_attachment = asset.kind == MediaAsset.Kind.DOCUMENT
            response["Content-Disposition"] = content_disposition_header(as_attachment, asset.original_name)
        return response

    @staticmethod
    def _allowed(request, asset, variant):
        if asset.visibility == MediaAsset.Visibility.PUBLIC:
            return True
        token = request.query_params.get("t")
        if token and asset.verify_token(token, variant):
            return True
        return asset.can_view(request.user)
