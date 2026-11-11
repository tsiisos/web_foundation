import io
import logging
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Pillow raises DecompressionBombError above twice this value
Image.MAX_IMAGE_PIXELS = settings.IMAGE_MAX_PIXELS

ALLOWED_IMAGE_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


class UploadRejected(Exception):
    """The uploaded file is not acceptable. The message is shown to the user."""


@dataclass
class ProcessedImage:
    data: bytes
    thumbnail: bytes
    extension: str
    content_type: str
    width: int
    height: int


def is_pdf(upload):
    head = upload.read(5)
    upload.seek(0)
    return head == b"%PDF-"


def _has_alpha(img):
    return img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info


def _encode(img, fmt):
    buf = io.BytesIO()
    if fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(buf, "JPEG", quality=85, optimize=True)
    elif fmt == "PNG":
        img.save(buf, "PNG", optimize=True)
    else:  # WEBP
        target = "RGBA" if _has_alpha(img) else "RGB"
        if img.mode != target:
            img = img.convert(target)
        img.save(buf, "WEBP", quality=85)
    return buf.getvalue()


def process_image(upload):
    """Validate an uploaded image, strip metadata (EXIF, GPS), limit its size, make a thumbnail."""
    try:
        img = Image.open(upload)
        fmt = img.format
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise UploadRejected("Only JPEG, PNG and WebP images are allowed.")
        if img.width * img.height > settings.IMAGE_MAX_PIXELS:
            raise UploadRejected("The image dimensions are too large.")
        img.load()
        img = ImageOps.exif_transpose(img)
    except UploadRejected:
        raise
    except Exception:
        logger.warning("Rejected unreadable image upload", exc_info=True)
        raise UploadRejected("The file is not a valid image.")

    try:
        side = settings.IMAGE_MAX_SIDE
        img.thumbnail((side, side), Image.Resampling.LANCZOS)  # only ever shrinks
        width, height = img.size
        thumb = img.copy()
        thumb.thumbnail((settings.THUMBNAIL_SIDE, settings.THUMBNAIL_SIDE), Image.Resampling.LANCZOS)
        extension, content_type = ALLOWED_IMAGE_FORMATS[fmt]
        return ProcessedImage(
            data=_encode(img, fmt),
            thumbnail=_encode(thumb, "WEBP"),
            extension=extension,
            content_type=content_type,
            width=width,
            height=height,
        )
    except Exception:
        logger.warning("Could not process image upload", exc_info=True)
        raise UploadRejected("The image could not be processed.")
