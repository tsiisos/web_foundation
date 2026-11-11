from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from rest_framework import serializers

from .models import MediaAsset
from .processing import UploadRejected, is_pdf, process_image


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
            "id", "kind", "visibility", "original_name", "content_type",
            "size", "width", "height", "url", "thumbnail_url", "created_at",
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

        if upload.size > settings.UPLOAD_MAX_BYTES:
            limit_mb = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
            raise serializers.ValidationError({"file": f"The file is larger than {limit_mb} MB."})

        asset = MediaAsset(owner=owner, visibility=visibility, original_name=_clean_name(upload.name))
        thumbnail_bytes = None
        try:
            if is_pdf(upload):
                if visibility == MediaAsset.Visibility.PUBLIC:
                    raise UploadRejected("Documents can only be uploaded as private files.")
                asset.kind = MediaAsset.Kind.DOCUMENT
                asset.content_type = "application/pdf"
                asset.size = upload.size
                data, extension = upload.read(), "pdf"
            else:
                processed = process_image(upload)
                asset.kind = MediaAsset.Kind.IMAGE
                asset.content_type = processed.content_type
                asset.size = len(processed.data)
                asset.width, asset.height = processed.width, processed.height
                data, extension, thumbnail_bytes = processed.data, processed.extension, processed.thumbnail
        except UploadRejected as exc:
            raise serializers.ValidationError({"file": str(exc)})

        name = asset.id.hex
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
        return asset
