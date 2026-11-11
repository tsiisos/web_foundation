import logging
import os
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

from .models import MediaAsset
from .processing import UploadRejected, process_image
from .video import VideoRejected, extract_frame, probe, remux

logger = logging.getLogger(__name__)


def enqueue_video(asset):
    try:
        process_video.delay(str(asset.pk))
    except Exception:
        logger.exception("Could not queue video processing for %s", asset.pk)
        return False
    return True


def _fail(asset, message):
    MediaAsset.objects.filter(pk=asset.pk, status=MediaAsset.Status.PROCESSING).update(
        status=MediaAsset.Status.FAILED, error=message[:255], file="", thumbnail=""
    )


@shared_task(time_limit=1800, soft_time_limit=1500)
def process_video(asset_id):
    asset = MediaAsset.objects.filter(pk=asset_id, status=MediaAsset.Status.PROCESSING).first()
    if asset is None or not asset.file:
        return  # deleted meanwhile, or already handled

    media_root = Path(settings.MEDIA_ROOT)
    workdir = media_root / "incoming"
    workdir.mkdir(parents=True, exist_ok=True)
    name = asset.id.hex
    source = media_root / asset.file.name
    remuxed = workdir / f"{name}.out.mp4"
    frame = workdir / f"{name}.frame.jpg"
    final_name = f"{asset.visibility}/{name}.mp4"
    final_path = media_root / final_name
    published = False
    try:
        if not source.exists():
            raise VideoRejected("The uploaded file is missing.")
        info = probe(source)
        remux(source, remuxed)
        extract_frame(remuxed, frame, min(1.0, info.duration / 2))
        if not frame.exists():
            raise VideoRejected("A preview image could not be created.")
        with frame.open("rb") as handle:
            thumbnail = process_image(handle).thumbnail

        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(remuxed, final_path)
        asset.thumbnail.save(f"{name}.webp", ContentFile(thumbnail), save=False)
        # update(), not save(): if the upload was deleted meanwhile, nothing is brought back
        published = bool(
            MediaAsset.objects.filter(pk=asset.pk, status=MediaAsset.Status.PROCESSING).update(
                file=final_name,
                thumbnail=asset.thumbnail.name,
                status=MediaAsset.Status.READY,
                size=final_path.stat().st_size,
                width=info.width,
                height=info.height,
                duration=info.duration,
                content_type="video/mp4",
                error="",
            )
        )
    except (VideoRejected, UploadRejected) as exc:
        _fail(asset, str(exc))
    except Exception:
        logger.exception("Video processing crashed for %s", asset_id)
        _fail(asset, "The video could not be processed.")
    finally:
        for leftover in (source, remuxed, frame):
            leftover.unlink(missing_ok=True)
        if not published:
            final_path.unlink(missing_ok=True)
            if asset.thumbnail:
                asset.thumbnail.storage.delete(asset.thumbnail.name)
