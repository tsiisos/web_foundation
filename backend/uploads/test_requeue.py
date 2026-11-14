from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import MediaAsset
from .tasks import requeue_stuck_videos

User = get_user_model()


class RequeueStuckVideosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner@example.com", "pass-12345-xyz", is_email_verified=True)

    def make(self, minutes_old, status="processing"):
        asset = MediaAsset.objects.create(
            owner=self.user, kind="video", visibility="private", status=status,
            file="incoming/x.mp4", original_name="x.mp4", content_type="video/mp4", size=1,
        )
        MediaAsset.objects.filter(pk=asset.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_old))
        return asset

    def test_only_old_processing_videos_are_requeued(self):
        old = self.make(30)
        self.make(2)                    # still fresh
        self.make(30, status="ready")   # already done
        self.make(30, status="failed")  # already failed
        with mock.patch("uploads.tasks.process_video") as task:
            requeue_stuck_videos()
        task.delay.assert_called_once_with(str(old.pk))
