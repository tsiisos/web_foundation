import uuid
from urllib.parse import quote

from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

SIGNER_SALT = "uploads.media"
VARIANTS = ("file", "thumbnail")


def file_path(instance, filename):
    return f"{instance.visibility}/{filename}"


def thumbnail_path(instance, filename):
    return f"{instance.visibility}/thumbs/{filename}"


class MediaAsset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_assets"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    visibility = models.CharField(max_length=20, choices=Visibility.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.READY)
    file = models.FileField(upload_to=file_path, max_length=255, blank=True)
    thumbnail = models.FileField(upload_to=thumbnail_path, max_length=255, blank=True)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["owner", "-created_at"])]

    def __str__(self):
        return f"{self.original_name} ({self.visibility})"

    def can_view(self, user):
        """Extend this per project (e.g. a renter may see the owner's contract)."""
        if self.visibility == self.Visibility.PUBLIC:
            return True
        return bool(user and user.is_authenticated and (user.pk == self.owner_id or user.is_staff))

    def token_lifetime(self, variant):
        # Players keep requesting parts of a video while seeking, so its link lives longer
        if self.kind == self.Kind.VIDEO and variant == "file":
            return settings.MEDIA_SIGNED_VIDEO_URL_SECONDS
        return settings.MEDIA_SIGNED_URL_SECONDS

    def signed_url(self, variant):
        token = TimestampSigner(salt=SIGNER_SALT).sign(f"{self.pk}:{variant}")
        path = reverse("media_serve", args=[self.pk, variant])
        return f"{path}?t={quote(token, safe='')}"

    def verify_token(self, token, variant):
        try:
            value = TimestampSigner(salt=SIGNER_SALT).unsign(
                token, max_age=self.token_lifetime(variant)
            )
        except BadSignature:  # includes SignatureExpired
            return False
        return value == f"{self.pk}:{variant}"

    def url_for(self, variant):
        if self.status != self.Status.READY:
            return None
        field = self.thumbnail if variant == "thumbnail" else self.file
        if not field:
            return None
        if self.visibility == self.Visibility.PUBLIC:
            return field.url
        return self.signed_url(variant)


@receiver(post_delete, sender=MediaAsset)
def delete_files_with_asset(sender, instance, **kwargs):
    for field in (instance.file, instance.thumbnail):
        if field:
            field.storage.delete(field.name)
