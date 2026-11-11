import io
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from .models import MediaAsset

User = get_user_model()

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="test_media_")
PASSWORD = "pass-12345-xyz"
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def make_image(fmt="JPEG", size=(800, 600), exif=False):
    buf = io.BytesIO()
    image = Image.new("RGB", size, (200, 60, 60))
    kwargs = {}
    if exif:
        data = Image.Exif()
        data[0x010F] = "TestCamera"
        kwargs["exif"] = data.tobytes()
    image.save(buf, fmt, **kwargs)
    ext = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}[fmt]
    return SimpleUploadedFile(f"photo.{ext}", buf.getvalue(), content_type=f"image/{ext}")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("owner@example.com", PASSWORD, is_email_verified=True)
        self.other = User.objects.create_user("other@example.com", PASSWORD, is_email_verified=True)
        self.client.force_authenticate(self.user)

    def upload(self, file, **extra):
        return self.client.post("/api/v1/media/", {"file": file, **extra}, format="multipart")

    # ---- who may upload ----

    def test_upload_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.upload(make_image()).status_code, 401)

    def test_upload_requires_verified_email(self):
        self.user.is_email_verified = False
        self.user.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.upload(make_image()).status_code, 403)

    # ---- images ----

    def test_public_image_upload(self):
        res = self.upload(make_image(), visibility="public")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["url"].startswith("/api/media/public/"))
        self.assertTrue(res.data["thumbnail_url"].startswith("/api/media/public/thumbs/"))
        self.assertEqual((res.data["width"], res.data["height"]), (800, 600))
        for url in (res.data["url"], res.data["thumbnail_url"]):
            path = os.path.join(TEST_MEDIA_ROOT, url.removeprefix("/api/media/"))
            self.assertTrue(os.path.exists(path), path)

    def test_upload_is_private_by_default(self):
        res = self.upload(make_image())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["visibility"], "private")
        self.assertTrue(res.data["url"].startswith(f"/api/v1/media/{res.data['id']}/file/?t="))
        asset = MediaAsset.objects.get(pk=res.data["id"])
        self.assertTrue(asset.file.name.startswith("private/"))
        self.assertTrue(os.path.exists(asset.file.path))

    def test_exif_metadata_is_stripped(self):
        upload = make_image(exif=True)
        self.assertGreater(len(Image.open(io.BytesIO(upload.read())).getexif()), 0)
        upload.seek(0)
        res = self.upload(upload)
        asset = MediaAsset.objects.get(pk=res.data["id"])
        self.assertEqual(len(Image.open(asset.file.path).getexif()), 0)

    def test_large_image_is_downscaled(self):
        res = self.upload(make_image(size=(3000, 1000)))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["width"], 2560)
        self.assertLess(res.data["height"], 1000)

    def test_png_and_webp_are_accepted(self):
        for fmt, content_type in (("PNG", "image/png"), ("WEBP", "image/webp")):
            res = self.upload(make_image(fmt=fmt))
            self.assertEqual(res.status_code, 201, res.data)
            self.assertEqual(res.data["content_type"], content_type)

    def test_fake_image_is_rejected(self):
        fake = SimpleUploadedFile("evil.jpg", b"<html><script>alert(1)</script></html>", content_type="image/jpeg")
        res = self.upload(fake)
        self.assertEqual(res.status_code, 400)
        self.assertIn("file", res.data)

    def test_gif_is_rejected(self):
        self.assertEqual(self.upload(make_image(fmt="GIF")).status_code, 400)

    @override_settings(UPLOAD_MAX_BYTES=100)
    def test_size_limit(self):
        self.assertEqual(self.upload(make_image()).status_code, 400)

    # ---- documents ----

    def test_pdf_is_private_only(self):
        pdf = SimpleUploadedFile("contract.pdf", PDF_BYTES, content_type="application/pdf")
        res = self.upload(pdf, visibility="private")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["kind"], "document")
        self.assertIsNone(res.data["thumbnail_url"])
        pdf = SimpleUploadedFile("contract.pdf", PDF_BYTES, content_type="application/pdf")
        self.assertEqual(self.upload(pdf, visibility="public").status_code, 400)

    # ---- downloading ----

    def test_owner_gets_private_file_and_thumbnail(self):
        res = self.upload(make_image())
        got = self.client.get(res.data["url"])
        self.assertEqual(got.status_code, 200)
        self.assertTrue(got["X-Accel-Redirect"].startswith("/api/protected-media/"))
        self.assertEqual(got["Content-Type"], "image/jpeg")
        thumb = self.client.get(res.data["thumbnail_url"])
        self.assertEqual(thumb.status_code, 200)
        self.assertIn("/thumbs/", thumb["X-Accel-Redirect"])
        self.assertEqual(thumb["Content-Type"], "image/webp")

    def test_signed_link_works_without_login(self):
        res = self.upload(make_image())
        anonymous = APIClient()
        url = res.data["url"]
        self.assertEqual(anonymous.get(url).status_code, 200)
        self.assertEqual(anonymous.get(url.split("?")[0]).status_code, 404)
        self.assertEqual(anonymous.get(url + "x").status_code, 404)

    def test_signed_link_is_valid_for_one_variant_only(self):
        res = self.upload(make_image())
        token_part = res.data["url"].split("?")[1]
        other_variant = f"/api/v1/media/{res.data['id']}/thumbnail/?{token_part}"
        self.assertEqual(APIClient().get(other_variant).status_code, 404)

    def test_signed_link_expires(self):
        res = self.upload(make_image())
        with override_settings(MEDIA_SIGNED_URL_SECONDS=-1):
            self.assertEqual(APIClient().get(res.data["url"]).status_code, 404)

    def test_other_users_cannot_see_private_file_but_staff_can(self):
        res = self.upload(make_image())
        plain_url = f"/api/v1/media/{res.data['id']}/file/"
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(plain_url).status_code, 404)
        staff = User.objects.create_user("staff@example.com", PASSWORD, is_staff=True, is_email_verified=True)
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.get(plain_url).status_code, 200)

    def test_public_file_endpoint_redirects_to_nginx_url(self):
        res = self.upload(make_image(), visibility="public")
        got = APIClient().get(f"/api/v1/media/{res.data['id']}/file/")
        self.assertEqual(got.status_code, 302)
        self.assertEqual(got["Location"], res.data["url"])

    # ---- list, detail, delete ----

    def test_list_shows_only_own_uploads(self):
        self.upload(make_image())
        self.upload(make_image())
        self.client.force_authenticate(self.other)
        self.upload(make_image())
        self.client.force_authenticate(self.user)
        res = self.client.get("/api/v1/media/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)

    def test_detail_and_delete_are_owner_only(self):
        res = self.upload(make_image())
        detail = f"/api/v1/media/{res.data['id']}/"
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 404)

    def test_delete_removes_files(self):
        res = self.upload(make_image(), visibility="public")
        asset = MediaAsset.objects.get(pk=res.data["id"])
        paths = [asset.file.path, asset.thumbnail.path]
        self.assertTrue(all(os.path.exists(p) for p in paths))
        self.assertEqual(self.client.delete(f"/api/v1/media/{res.data['id']}/").status_code, 204)
        self.assertFalse(any(os.path.exists(p) for p in paths))
