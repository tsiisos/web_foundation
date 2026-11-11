from django.contrib import admin

from .models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("original_name", "owner", "kind", "visibility", "size", "created_at")
    list_filter = ("kind", "visibility")
    search_fields = ("original_name", "owner__email")
    readonly_fields = [f.name for f in MediaAsset._meta.fields]

    def has_add_permission(self, request):
        return False
