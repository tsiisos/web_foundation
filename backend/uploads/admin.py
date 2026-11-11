from django.contrib import admin, messages

from .models import MediaAsset
from .tasks import enqueue_video


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("original_name", "owner", "kind", "status", "visibility", "size", "created_at")
    list_filter = ("kind", "status", "visibility")
    search_fields = ("original_name", "owner__email")
    readonly_fields = [f.name for f in MediaAsset._meta.fields]
    actions = ["requeue_stuck_videos"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Re-queue selected videos stuck in processing")
    def requeue_stuck_videos(self, request, queryset):
        stuck = queryset.filter(kind=MediaAsset.Kind.VIDEO, status=MediaAsset.Status.PROCESSING)
        queued = sum(1 for asset in stuck if enqueue_video(asset))
        self.message_user(request, f"Queued {queued} video(s).", messages.SUCCESS)
