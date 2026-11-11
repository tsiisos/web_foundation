import json
import logging
import subprocess
from dataclasses import dataclass

from .processing import ALLOWED_BRANDS

logger = logging.getLogger(__name__)

ALLOWED_AUDIO = {"aac", "mp3"}
ALLOWED_PIXEL_FORMATS = {"yuv420p", "yuvj420p"}


class VideoRejected(Exception):
    """The video is not acceptable. The message is shown to the user."""


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float


def _run(cmd, timeout):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        raise VideoRejected("Processing the video took too long.")
    except subprocess.CalledProcessError as exc:
        logger.warning("%s failed: %s", cmd[0], exc.stderr.decode(errors="replace")[-500:])
        raise VideoRejected("The video could not be read.")


def probe(path):
    """Check that the file is an MP4 with H.264 video (and AAC/MP3 audio, if any)."""
    result = _run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        timeout=60,
    )
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise VideoRejected("The video could not be read.")

    fmt = data.get("format") or {}
    brand = (fmt.get("tags") or {}).get("major_brand")
    if "mp4" not in fmt.get("format_name", "") or brand not in ALLOWED_BRANDS:
        raise VideoRejected("Only MP4 videos are supported.")

    streams = data.get("streams") or []
    videos = [
        s for s in streams
        if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")
    ]
    if not videos or videos[0].get("codec_name") != "h264" or videos[0].get("pix_fmt") not in ALLOWED_PIXEL_FORMATS:
        raise VideoRejected("The video must be H.264 (yuv420p) inside an MP4 file.")
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if audios and audios[0].get("codec_name") not in ALLOWED_AUDIO:
        raise VideoRejected("The audio track must be AAC or MP3.")

    video = videos[0]
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    for side_data in video.get("side_data_list") or []:
        if "rotation" in side_data and abs(int(float(side_data["rotation"]))) % 180 == 90:
            width, height = height, width
    try:
        duration = float(fmt.get("duration") or video.get("duration") or 0)
    except ValueError:
        duration = 0.0
    if width <= 0 or height <= 0 or duration <= 0:
        raise VideoRejected("The video could not be read.")
    return VideoInfo(width=width, height=height, duration=duration)


def remux(source, target):
    """Copy the streams without re-encoding: drops metadata (e.g. GPS) and moves the index to the front."""
    _run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c", "copy",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-movflags", "+faststart",
            "-f", "mp4", str(target),
        ],
        timeout=900,
    )


def extract_frame(source, target, at_seconds):
    _run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{at_seconds:.2f}", "-i", str(source),
            "-frames:v", "1", "-q:v", "2", str(target),
        ],
        timeout=120,
    )
