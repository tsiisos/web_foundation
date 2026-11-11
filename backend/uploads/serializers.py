from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import MediaAsset
from .processing import UploadRejected, process_image, sniff_kind
from .tasks import enqueue_video


class ProcessingUnavailable(APIException):
    status_code = 503
    default_detail = "Video processing is temporarily unavailable. Please try again later."
    default_code = "processing_unavailable"


def _clean_name(name):
    try:
        return get_valid_filename(name)[:255] or "upload"
    except SuspiciousFileOperation:
        return "upload"


class MediaAssetSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = (
            "id", "kind", "visibility", "status", "error", "original_name", "content_type",
            "size", "width", "height", "duration", "url", "thumbnail_url", "created_at",
        )
        read_only_fields = fields

    def get_url(self, obj):
        return obj.url_for("file")

    def get_thumbnail_url(self, obj):
        return obj.url_for("thumbnail")


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    visibility = serializers.ChoiceField(
        choices=MediaAsset.Visibility.choices, default=MediaAsset.Visibility.PRIVATE
    )

    def create(self, validated_data):
        upload = validated_data["file"]
        visibility = validated_data["visibility"]
        owner = self.context["request"].user

        kind = sniff_kind(upload)
        limit = settings.VIDEO_MAX_BYTES if kind == MediaAsset.Kind.VIDEO else settings.UPLOAD_MAX_BYTES
        if upload.size > limit:
            raise serializers.ValidationError({"file": f"The file is larger than {limit // (1024 * 1024)} MB."})

        asset = MediaAsset(owner=owner, visibility=visibility, kind=kind, original_name=_clean_name(upload.name))
        name = asset.id.hex
        data = extension = thumbnail_bytes = None
        try:
            if kind == MediaAsset.Kind.DOCUMENT:
                if visibility == MediaAsset.Visibility.PUBLIC:
                    raise UploadRejected("Documents can only be uploaded as private files.")
                asset.content_type = "application/pdf"
                asset.size = upload.size
                data, extension = upload.read(), "pdf"
            elif kind == MediaAsset.Kind.VIDEO:
                asset.status = MediaAsset.Status.PROCESSING
                asset.content_type = "video/mp4"
                asset.size = upload.size
            else:
                processed = process_image(upload)
                asset.content_type = processed.content_type
                asset.size = len(processed.data)
                asset.width, asset.height = processed.width, processed.height
                data, extension, thumbnail_bytes = processed.data, processed.extension, processed.thumbnail
        except UploadRejected as exc:
            raise serializers.ValidationError({"file": str(exc)})

        if kind == MediaAsset.Kind.VIDEO:
            # Raw upload goes to a folder nginx never serves, until the worker has checked it
            asset.file = asset.file.storage.save(f"incoming/{name}.mp4", upload)
        else:
            asset.file.save(f"{name}.{extension}", ContentFile(data), save=False)
            if thumbnail_bytes:
                asset.thumbnail.save(f"{name}.webp", ContentFile(thumbnail_bytes), save=False)
        try:
            asset.save()
        except Exception:
            for field in (asset.file, asset.thumbnail):
                if field:
                    field.storage.delete(field.name)
            raise

        if kind == MediaAsset.Kind.VIDEO and not enqueue_video(asset):
            asset.delete()  # also removes the raw upload
            raise ProcessingUnavailable()
        return asset
