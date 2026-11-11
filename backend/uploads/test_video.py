import json
import os
import shutil
import subprocess
import tempfile
import unittest

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from .models import MediaAsset

User = get_user_model()

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="test_media_video_")
FFMPEG = shutil.which("ffmpeg")


def make_mp4(*, video=True, audio=True, pix_fmt="yuv420p", metadata=False):
    """Build a tiny real MP4 with ffmpeg."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.mp4")
        args = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
        if video:
            args += ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=10"]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440"]
        args += ["-t", "1"]
        if video:
            args += ["-c:v", "libx264", "-pix_fmt", pix_fmt]
        if audio:
            args += ["-c:a", "aac"]
        if metadata:
            args += ["-metadata", "title=Secret title", "-metadata", "location=+60.1699+024.9384/"]
        args += ["-f", "mp4", out]
        subprocess.run(args, check=True)
        with open(out, "rb") as handle:
            return SimpleUploadedFile("clip.mp4", handle.read(), content_type="video/mp4")


def tags_of(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path],
        capture_output=True, check=True,
    )
    tags = json.loads(result.stdout)["format"].get("tags") or {}
    return {key.lower() for key in tags}


@unittest.skipUnless(FFMPEG, "ffmpeg is not installed")
@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("owner@example.com", "pass-12345-xyz", is_email_verified=True)
        self.client.force_authenticate(self.user)

    def upload(self, file, **extra):
        return self.client.post("/api/v1/media/", {"file": file, **extra}, format="multipart")

    def upload_ok(self, file, **extra):
        res = self.upload(file, **extra)
        self.assertEqual(res.status_code, 201, res.data)
        # Tasks run immediately in tests, so the database already holds the final result
        return MediaAsset.objects.get(pk=res.data["id"]), res

    def test_video_is_processed_and_published(self):
        asset, res = self.upload_ok(make_mp4(), visibility="public")
        self.assertEqual(res.data["kind"], "video")
        self.assertEqual(res.data["status"], "processing")  # what the client sees right after upload
        self.assertIsNone(res.data["url"])
        self.assertEqual(asset.status, "ready")
        self.assertEqual(asset.file.name, f"public/{asset.id.hex}.mp4")
        self.assertEqual((asset.width, asset.height), (320, 240))
        self.assertGreater(asset.duration, 0.5)
        self.assertTrue(os.path.exists(asset.file.path))
        self.assertTrue(os.path.exists(asset.thumbnail.path))
        self.assertFalse(os.path.exists(os.path.join(TEST_MEDIA_ROOT, "incoming", f"{asset.id.hex}.mp4")))
        detail = self.client.get(f"/api/v1/media/{asset.id}/")
        self.assertEqual(detail.data["status"], "ready")
        self.assertTrue(detail.data["url"].startswith("/api/media/public/"))

    def test_private_video_is_served_through_signed_link(self):
        asset, _ = self.upload_ok(make_mp4())
        url = self.client.get(f"/api/v1/media/{asset.id}/").data["url"]
        self.assertIn("/file/?t=", url)
        got = APIClient().get(url)
        self.assertEqual(got.status_code, 200)
        self.assertTrue(got["X-Accel-Redirect"].startswith("/api/protected-media/"))
        self.assertEqual(got["Content-Type"], "video/mp4")
        self.assertTrue(got["Content-Disposition"].startswith("inline"))

    def test_metadata_is_stripped(self):
        upload = make_mp4(metadata=True)
        with tempfile.NamedTemporaryFile(suffix=".mp4") as original:
            original.write(upload.read())
            original.flush()
            self.assertIn("title", tags_of(original.name))  # the test file really has metadata
        upload.seek(0)
        asset, _ = self.upload_ok(upload)
        self.assertEqual(asset.status, "ready")
        tags = tags_of(asset.file.path)
        self.assertNotIn("title", tags)
        self.assertNotIn("location", tags)

    def test_mp4_without_video_stream_fails(self):
        asset, _ = self.upload_ok(make_mp4(video=False))
        self.assertEqual(asset.status, "failed")
        self.assertTrue(asset.error)
        self.assertFalse(asset.file)
        self.assertEqual(os.listdir(os.path.join(TEST_MEDIA_ROOT, "incoming")), [])

    def test_unsupported_pixel_format_fails(self):
        asset, _ = self.upload_ok(make_mp4(pix_fmt="yuv444p"))
        self.assertEqual(asset.status, "failed")

    @override_settings(VIDEO_MAX_BYTES=100)
    def test_video_size_limit(self):
        self.assertEqual(self.upload(make_mp4()).status_code, 400)

    def test_text_file_named_mp4_is_rejected(self):
        fake = SimpleUploadedFile("evil.mp4", b"<html>not a video</html>", content_type="video/mp4")
        self.assertEqual(self.upload(fake).status_code, 400)

    def test_unfinished_video_is_not_served(self):
        asset = MediaAsset.objects.create(
            owner=self.user, kind="video", visibility="private", status="processing",
            file="incoming/x.mp4", original_name="x.mp4", content_type="video/mp4", size=1,
        )
        self.assertEqual(self.client.get(f"/api/v1/media/{asset.id}/file/").status_code, 404)
        self.assertIsNone(self.client.get(f"/api/v1/media/{asset.id}/").data["url"])

    def test_video_link_outlives_image_links(self):
        asset, _ = self.upload_ok(make_mp4())
        detail = self.client.get(f"/api/v1/media/{asset.id}/").data
        with override_settings(MEDIA_SIGNED_URL_SECONDS=-1):
            self.assertEqual(APIClient().get(detail["url"]).status_code, 200)
            self.assertEqual(APIClient().get(detail["thumbnail_url"]).status_code, 404)

    def test_delete_removes_video_files(self):
        asset, _ = self.upload_ok(make_mp4(), visibility="public")
        paths = [asset.file.path, asset.thumbnail.path]
        self.assertEqual(self.client.delete(f"/api/v1/media/{asset.id}/").status_code, 204)
        self.assertFalse(any(os.path.exists(p) for p in paths))
